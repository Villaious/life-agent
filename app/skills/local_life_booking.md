# Local Life Booking Skill

## Purpose

将本地生活预约流程中的稳定经验沉淀为可复用规则，帮助后续开发者扩展服务匹配、时间确认、订单草单、权限审计和失败恢复。

## Learn

预约任务通常包含以下稳定信息：

- 用户意图：服务类别、服务内容、地点、时间偏好。
- 服务商候选：价格、服务范围、履约时长、评分、库存锁定状态。
- 时间确认：开始时间、结束时间、时区、是否需要二次确认、库存锁定。
- 订单草单：任务 ID、订单状态、服务商快照、时间快照、价格快照。
- 安全边界：外部 API 权限、用户隐私上下文权限、订单写入权限。

## Patch

扩展流程时遵循以下顺序：

1. 先补充 `app/models/booking.py` 和 `app/models/state.py` 的结构化字段。
2. 在 `app/integrations/local_life_client.py` 做真实接口字段归一化。
3. 将外部能力封装成 `BaseTool`，并声明 `required_permissions`。
4. 在 `BookingAgent._build_graph()` 注册节点和条件边。
5. 工具失败时写入 `tool_error` 和 `audit_events`，再进入统一失败节点。
6. 需要持久化时使用 `booking_tasks`、`booking_orders`、`tool_audit_logs`。

## Validate

每次修改预约流程后至少覆盖以下测试：

- 多轮预约：第一轮缺信息，第二轮补齐后成功。
- 信息缺失：返回 `needs_info` 和缺失字段。
- LLM 解析失败：回退本地规则。
- 工具失败：进入统一失败响应。
- 接口超时：不会创建订单。
- 权限拒绝：缺少外部 API、隐私上下文或订单写入权限时停止执行。

## Review Rules

- 不要把真实接口字段散落在 Agent 节点中，统一放在 integration client 做归一化。
- 不要在前端推断权限结果，权限判断必须由后端 `ToolSandbox` 完成。
- 不要在订单节点直接信任候选服务商原始响应，必须保存归一化快照。
- 不要让工具异常直接冒泡到 API 响应，统一转成 `ToolResult(ok=False)`。
