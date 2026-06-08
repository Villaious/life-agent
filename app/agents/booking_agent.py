import json
from typing import Any

from langgraph.graph import END, StateGraph

from app.core.agent import BaseAgent
from app.models.booking import BookingRequest, BookingResponse, BookingStatus
from app.models.state import BookingGraphState
from app.tools.base import BaseTool
from app.tools.builtin.booking_tools import OrderDraftTool, ServiceMatchTool, SlotConfirmTool
from app.tools.policy import ToolContext, ToolPolicy
from app.tools.sandbox import ToolSandbox


class BookingAgent(BaseAgent):
    def __init__(self, tools: list[BaseTool] | None = None) -> None:
        super().__init__(
            name="本地生活预约Agent",
            system_prompt=(
                "你是本地生活服务预约助手，负责理解用户需求、补全信息、匹配服务、"
                "确认时间并生成预约草单。"
            ),
            tools=tools or [ServiceMatchTool(), SlotConfirmTool(), OrderDraftTool()],
        )
        self.sandbox = ToolSandbox(self.tools, ToolPolicy())
        self.graph = self._build_graph()

    async def run(self, user_input: str, **kwargs: object) -> BookingResponse:
        request = kwargs.get("request")
        if not isinstance(request, BookingRequest):
            request = BookingRequest(user_id="anonymous", message=user_input)

        initial_state: BookingGraphState = {
            "request": request,
            "tool_context": self._build_tool_context(request),
            "audit_events": [],
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state["response"]

    def _build_graph(self):
        graph = StateGraph(BookingGraphState)
        graph.add_node("understand_intent", self._understand_intent_node)
        graph.add_node("build_missing_info_response", self._build_missing_info_response_node)
        graph.add_node("match_service", self._match_service_node)
        graph.add_node("confirm_slot", self._confirm_slot_node)
        graph.add_node("create_order", self._create_order_node)
        graph.add_node("build_success_response", self._build_success_response_node)
        graph.add_node("build_tool_error_response", self._build_tool_error_response_node)

        graph.set_entry_point("understand_intent")
        graph.add_conditional_edges(
            "understand_intent",
            self._route_after_intent,
            {
                "needs_info": "build_missing_info_response",
                "continue": "match_service",
            },
        )
        graph.add_edge("build_missing_info_response", END)
        graph.add_conditional_edges(
            "match_service",
            self._route_after_tool,
            {"failed": "build_tool_error_response", "continue": "confirm_slot"},
        )
        graph.add_conditional_edges(
            "confirm_slot",
            self._route_after_tool,
            {"failed": "build_tool_error_response", "continue": "create_order"},
        )
        graph.add_conditional_edges(
            "create_order",
            self._route_after_tool,
            {"failed": "build_tool_error_response", "continue": "build_success_response"},
        )
        graph.add_edge("build_tool_error_response", END)
        graph.add_edge("build_success_response", END)
        return graph.compile()

    async def _understand_intent_node(self, state: BookingGraphState) -> BookingGraphState:
        request = state["request"]
        intent = await self._understand_intent(request)
        missing_fields = self._find_missing_fields(intent)
        return {
            **state,
            "current_step": "understand_intent",
            "intent": intent,
            "missing_fields": missing_fields,
        }

    async def _build_missing_info_response_node(
        self, state: BookingGraphState
    ) -> BookingGraphState:
        return {
            **state,
            "current_step": "build_missing_info_response",
            "response": BookingResponse(
                status=BookingStatus.NEEDS_INFO,
                reply="我还需要补充一些信息，才能继续为你预约。",
                missing_fields=state.get("missing_fields", []),
            ),
        }

    async def _match_service_node(self, state: BookingGraphState) -> BookingGraphState:
        intent = state["intent"]
        result = await self._run_tool(
            state,
            "service_match",
            {
                "service_category": intent["service_category"],
                "location": intent["location"],
            },
            "candidates",
        )
        if not result["ok"]:
            return self._with_tool_error(state, "match_service", result)
        return {
            **state,
            "current_step": "match_service",
            "service_candidates": result["data"],
            "audit_events": self._append_audit_event(
                state,
                "service_match",
                "ok",
                request_payload={
                    "service_category": intent["service_category"],
                    "location": intent["location"],
                },
                response_payload={"candidates": result["data"]},
            ),
        }

    async def _confirm_slot_node(self, state: BookingGraphState) -> BookingGraphState:
        result = await self._run_tool(state, "slot_confirm", state["intent"], "slot")
        if not result["ok"]:
            return self._with_tool_error(state, "confirm_slot", result)
        return {
            **state,
            "current_step": "confirm_slot",
            "selected_slot": result["data"],
            "audit_events": self._append_audit_event(
                state,
                "slot_confirm",
                "ok",
                request_payload=state["intent"],
                response_payload={"slot": result["data"]},
            ),
        }

    async def _create_order_node(self, state: BookingGraphState) -> BookingGraphState:
        candidates = state.get("service_candidates", [])
        result = await self._run_tool(
            state,
            "order_draft",
            {
                "slot": state.get("selected_slot"),
                "provider": candidates[0] if candidates else None,
            },
            "order",
        )
        if not result["ok"]:
            return self._with_tool_error(state, "create_order", result)
        return {
            **state,
            "current_step": "create_order",
            "order": result["data"],
            "audit_events": self._append_audit_event(
                state,
                "order_draft",
                "ok",
                request_payload={
                    "slot": state.get("selected_slot"),
                    "provider": candidates[0] if candidates else None,
                },
                response_payload={"order": result["data"]},
            ),
        }

    async def _build_success_response_node(self, state: BookingGraphState) -> BookingGraphState:
        order = state.get("order", {})
        return {
            **state,
            "current_step": "build_success_response",
            "response": BookingResponse(
                status=BookingStatus.CREATED,
                reply="已为你生成预约草单，请确认服务、时间和地址信息。",
                task_id=order.get("task_id"),
                candidates=state.get("service_candidates", []),
            ),
        }

    async def _build_tool_error_response_node(self, state: BookingGraphState) -> BookingGraphState:
        error = state.get("tool_error", {})
        error_code = error.get("error", "tool_failed")
        reply = "预约服务暂时不可用，请稍后再试。"
        if error_code == "permission_denied":
            reply = "当前任务缺少调用该服务能力的权限，请确认授权后再继续。"

        return {
            **state,
            "current_step": "build_tool_error_response",
            "response": BookingResponse(
                status=BookingStatus.FAILED,
                reply=reply,
                candidates=state.get("service_candidates", []),
            ),
        }

    def _route_after_intent(self, state: BookingGraphState) -> str:
        return "needs_info" if state.get("missing_fields") else "continue"

    def _route_after_tool(self, state: BookingGraphState) -> str:
        return "failed" if state.get("tool_error") else "continue"

    async def _understand_intent(self, request: BookingRequest) -> dict[str, Any]:
        heuristic_intent = {
            "raw_text": request.message,
            "service_category": self._guess_category(request.message),
            "location": request.context.get("location"),
            "time_preference": request.context.get("time_preference"),
        }
        if not self.llm.is_live:
            return heuristic_intent

        prompt = (
            "请从本地生活预约请求中抽取结构化意图，只返回 JSON。"
            "字段包括 raw_text、service_category、location、time_preference。"
            "service_category 可取 home_cleaning、repair、beauty、unknown。"
            f"\n用户请求：{request.message}"
            f"\n已知上下文：{json.dumps(request.context, ensure_ascii=False)}"
        )
        try:
            content = await self.llm.complete(prompt, system_prompt=self.system_prompt)
            parsed = json.loads(content)
        except Exception:
            return heuristic_intent

        return {
            "raw_text": request.message,
            "service_category": parsed.get("service_category") or heuristic_intent["service_category"],
            "location": parsed.get("location") or heuristic_intent["location"],
            "time_preference": parsed.get("time_preference") or heuristic_intent["time_preference"],
        }

    def _find_missing_fields(self, intent: dict[str, Any]) -> list[str]:
        missing_fields: list[str] = []
        if not intent["raw_text"].strip():
            missing_fields.append("service_intent")
        if not intent["location"]:
            missing_fields.append("location")
        if not intent["time_preference"]:
            missing_fields.append("time_preference")
        return missing_fields

    def _guess_category(self, text: str) -> str:
        if "保洁" in text or "打扫" in text:
            return "home_cleaning"
        if "维修" in text:
            return "repair"
        if "美甲" in text:
            return "beauty"
        return "unknown"

    def _build_tool_context(self, request: BookingRequest) -> ToolContext:
        raw_permissions = request.context.get("permissions")
        if raw_permissions is None:
            permissions = {
                "booking:match",
                "booking:slot",
                "booking:order",
                "external_api:local_life",
                "privacy:user_context",
                "order:write",
            }
        elif isinstance(raw_permissions, list):
            permissions = {str(permission) for permission in raw_permissions}
        else:
            permissions = set()

        return ToolContext(
            user_id=request.user_id,
            task_id=request.session_id,
            permissions=permissions,
            privacy_scopes={"location", "time_preference", "service_intent"},
        )

    async def _run_tool(
        self,
        state: BookingGraphState,
        name: str,
        payload: dict[str, Any],
        key: str,
    ) -> dict[str, Any]:
        result = await self.sandbox.call(name, payload, state["tool_context"])
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error", "tool_failed"), "tool": name}
        data = result.get("data", {})
        if key not in data:
            return {"ok": False, "error": "invalid_tool_result", "tool": name}
        return {"ok": True, "data": data[key], "tool": name}

    def _with_tool_error(
        self,
        state: BookingGraphState,
        step: str,
        result: dict[str, Any],
    ) -> BookingGraphState:
        tool = str(result.get("tool", "unknown"))
        return {
            **state,
            "current_step": step,
            "tool_error": {
                "step": step,
                "tool": tool,
                "error": result.get("error", "tool_failed"),
            },
            "audit_events": self._append_audit_event(
                state,
                tool,
                str(result.get("error", "tool_failed")),
                error=str(result.get("error", "tool_failed")),
            ),
        }

    def _append_audit_event(
        self,
        state: BookingGraphState,
        tool: str,
        status: str,
        request_payload: dict[str, Any] | None = None,
        response_payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> list[dict[str, Any]]:
        context = state["tool_context"]
        return [
            *state.get("audit_events", []),
            {
                "step": state.get("current_step"),
                "tool": tool,
                "status": status,
                "permissions": sorted(context.permissions),
                "privacy_scopes": sorted(context.privacy_scopes or []),
                "request_payload": self._jsonable(request_payload),
                "response_payload": self._jsonable(response_payload),
                "error": error,
            },
        ]

    def _jsonable(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        if isinstance(value, dict):
            return {key: self._jsonable(item) for key, item in value.items()}
        return value
