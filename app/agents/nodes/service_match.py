import logging

from app.integrations.amap_client import AmapClient
from app.models.state import BookingGraphState

logger = logging.getLogger(__name__)


async def match_service(state: BookingGraphState) -> BookingGraphState:
    """
    通过高德地图 API 搜索目标地点附近的家政保洁等服务。

    从 intent 中提取 location（可以是地址字符串或经纬度坐标），
    调用高德周边搜索找到附近的服务商，并归一化为 ServiceCandidate 列表。
    """
    intent = state.get("intent", {})
    location_raw = intent.get("location", "")

    if not location_raw:
        state["service_candidates"] = []
        state["tool_error"] = {
            "step": "match_service",
            "error": "缺少目标位置信息，无法搜索附近服务",
        }
        logger.warning("match_service: 缺少 location，跳过搜索")
        return state

    try:
        client = AmapClient()

        # 判断 location 是否为经纬度坐标（格式：经度,纬度）
        if _is_coordinate(location_raw):
            candidates = await client.search_housekeeping_services(
                location=location_raw,
            )
        else:
            # 将地址解析为坐标后再搜索
            city = intent.get("city") or _extract_city(location_raw)
            _, candidates = await client.search_services_by_address(
                address=location_raw,
                city=city,
            )

        state["service_candidates"] = candidates

        if not candidates:
            logger.info("match_service: 在位置 %s 附近未找到家政服务", location_raw)

    except ValueError as exc:
        logger.error("match_service: 地址解析失败 - %s", exc)
        state["service_candidates"] = []
        state["tool_error"] = {
            "step": "match_service",
            "error": str(exc),
        }
    except Exception as exc:
        logger.error("match_service: 搜索服务时发生异常 - %s", exc, exc_info=True)
        state["service_candidates"] = []
        state["tool_error"] = {
            "step": "match_service",
            "error": f"搜索附近服务失败: {exc}",
        }

    return state


def _is_coordinate(value: str) -> bool:
    """判断字符串是否为经纬度坐标格式（如 "116.397428,39.90923"）。"""
    value = value.strip()
    parts = value.split(",")
    if len(parts) != 2:
        return False
    try:
        float(parts[0])
        float(parts[1])
        return True
    except ValueError:
        return False


def _extract_city(address: str) -> str | None:
    """从地址中尝试提取城市名（简单启发式提取前两个字符）。"""
    # 中国地级市通常在地址开头，如 "深圳市南山区..."
    if len(address) >= 2 and address[0] and address[1]:
        # 如果第二个字是 "市"，大概率是城市名
        if "市" in address[:3]:
            idx = address.index("市")
            return address[: idx + 1]
    return None
