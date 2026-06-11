"""
高德地图(AMap) API 客户端
用于搜索目标地点附近的家政保洁等服务商（POI 搜索）。
"""

from typing import Any

import httpx

from app.core.config import settings
from app.models.booking import ServiceCandidate, ServiceArea


# 家政服务相关的高德 POI 类型编码
HOUSEKEEPING_TYPECODES = [
    "060100",  # 家政服务
    "060101",  # 保洁公司
    "060102",  # 搬家服务
    "060103",  # 管道疏通
    "060104",  # 家电维修
    "060107",  # 其他家政服务
]

# 默认搜索关键词
DEFAULT_KEYWORDS = ["家政", "保洁", "清洁", "保姆", "月嫂", "钟点工"]

# AMap REST API 基础 URL
AMAP_BASE_URL = "https://restapi.amap.com/v3"


class AmapClient:
    """高德地图 API 客户端，提供地理编码和周边 POI 搜索能力。"""

    def __init__(
        self,
        api_key: str | None = None,
        search_radius: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key or settings.amap_api_key
        self.search_radius = search_radius if search_radius is not None else settings.amap_search_radius
        self.timeout = timeout if timeout is not None else settings.amap_timeout

    async def geocode(self, address: str, city: str | None = None) -> dict[str, Any] | None:
        """地理编码：将结构化地址转换为经纬度坐标。

        Args:
            address: 结构化地址（如 "深圳市南山区科技园"）
            city: 指定城市，可选

        Returns:
            包含 location（经纬度）、level（精度等级）等信息的字典，失败返回 None
        """
        params: dict[str, str] = {
            "key": self.api_key,
            "address": address,
        }
        if city:
            params["city"] = city

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{AMAP_BASE_URL}/geocode/geo", params=params)
            data = response.json()

        if data.get("status") != "1" or data.get("count") == "0":
            return None

        geocodes = data.get("geocodes", [])
        if not geocodes:
            return None

        return {
            "location": geocodes[0].get("location"),
            "level": geocodes[0].get("level"),
            "city": geocodes[0].get("city"),
            "district": geocodes[0].get("district"),
            "adcode": geocodes[0].get("adcode"),
            "formatted_address": geocodes[0].get("formatted_address"),
        }

    async def search_nearby(
        self,
        location: str,
        keywords: str | None = None,
        types: str | None = None,
        radius: int | None = None,
        offset: int = 20,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """周边 POI 搜索：在指定坐标附近搜索家政保洁等服务商。

        Args:
            location: 中心点坐标，格式 "经度,纬度"（如 "116.397428,39.90923"）
            keywords: 搜索关键词，多个用 | 分隔
            types: POI 类型编码，多个用 | 分隔
            radius: 搜索半径，单位米，默认 3000
            offset: 每页记录数，最大 25
            page: 页码

        Returns:
            POI 列表，每个 POI 包含 name、address、location、type、typecode 等字段
        """
        if not self.api_key:
            raise ValueError("AMAP_API_KEY 未配置，请在 .env 中设置 AMAP_API_KEY")

        params: dict[str, str | int] = {
            "key": self.api_key,
            "location": location,
            "offset": offset,
            "page": page,
            "extensions": "base",
        }

        if keywords:
            params["keywords"] = keywords
        if types:
            params["types"] = types
        if radius is not None:
            params["radius"] = radius
        else:
            params["radius"] = self.search_radius

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{AMAP_BASE_URL}/place/around", params=params)
            data = response.json()

        if data.get("status") != "1":
            return []

        return data.get("pois", [])

    async def search_housekeeping_services(
        self,
        location: str,
        radius: int | None = None,
    ) -> list[ServiceCandidate]:
        """搜索目标地点附近的家政保洁服务商，并归一化为 ServiceCandidate 列表。

        支持两种搜索策略：
        1. 按类型编码搜索（精确匹配家政服务类 POI）
        2. 按关键词搜索（覆盖更广的结果）

        Args:
            location: 中心点坐标，格式 "经度,纬度"
            radius: 搜索半径，单位米，默认 3000

        Returns:
            归一化后的 ServiceCandidate 列表
        """
        # 策略一：按类型编码搜索
        type_keywords = "|".join(HOUSEKEEPING_TYPECODES)
        type_pois = await self.search_nearby(
            location=location,
            types=type_keywords,
            radius=radius,
        )

        # 策略二：按关键词搜索（补充结果）
        keyword_pois = await self.search_nearby(
            location=location,
            keywords="|".join(DEFAULT_KEYWORDS),
            radius=radius,
        )

        # 合并去重（按 POI id）
        seen_ids: set[str] = set()
        candidates: list[ServiceCandidate] = []

        for poi in type_pois + keyword_pois:
            poi_id = str(poi.get("id", ""))
            if poi_id in seen_ids:
                continue
            seen_ids.add(poi_id)

            candidate = self._poi_to_candidate(poi)
            candidates.append(candidate)

        return candidates

    async def search_services_by_address(
        self,
        address: str,
        city: str | None = None,
        radius: int | None = None,
    ) -> tuple[str, list[ServiceCandidate]]:
        """按地址搜索附近的家政保洁服务。

        先对地址进行地理编码，再在坐标点附近搜索服务商。

        Args:
            address: 目标地址（如 "深圳市南山区科技园南区"）
            city: 指定城市（可选，有助于提高地理编码精度）
            radius: 搜索半径，单位米

        Returns:
            (坐标字符串, ServiceCandidate 列表) 的元组

        Raises:
            ValueError: 地址解析失败时抛出
        """
        geo_result = await self.geocode(address, city=city)
        if not geo_result or not geo_result.get("location"):
            raise ValueError(f"地址解析失败，无法获取坐标：{address}")

        location = geo_result["location"]
        candidates = await self.search_housekeeping_services(
            location=location,
            radius=radius,
        )
        return location, candidates

    def _poi_to_candidate(self, poi: dict[str, Any]) -> ServiceCandidate:
        """将高德 POI 数据归一化为 ServiceCandidate。"""
        pname = poi.get("pname", "")
        cityname = poi.get("cityname", "")
        adname = poi.get("adname", "")
        address = poi.get("address", "")
        display_location = self._format_display_location(cityname or pname, adname, address)
        sanitized_raw = {key: value for key, value in poi.items() if key != "location"}

        return ServiceCandidate(
            provider_id=str(poi.get("id", "")),
            name=str(poi.get("name", "")),
            category=self._categorize_poi(poi),
            location=display_location,
            phone=self._normalize_tel(poi.get("tel")),
            score=None,  # 高德 POI 不提供评分
            service_area=ServiceArea(
                city=cityname or pname,
                district=adname,
                address_hint=address,
                radius_km=self.search_radius / 1000.0,
            ),
            raw=sanitized_raw,
        )

    def _format_display_location(
        self,
        city: str | None,
        district: str | None,
        address: str | list[Any] | None,
    ) -> str | None:
        if isinstance(address, list):
            address_text = " ".join(str(item) for item in address if item)
        else:
            address_text = str(address or "")
        parts = [part for part in [city, district, address_text] if part]
        return " ".join(parts) if parts else None

    def _normalize_tel(self, tel: Any) -> str | None:
        if isinstance(tel, list):
            values = [str(item) for item in tel if item]
            return " / ".join(values) if values else None
        text = str(tel or "").strip()
        return text or None

    def _categorize_poi(self, poi: dict[str, Any]) -> str:
        """根据高德 POI 的 type/typecode 推断服务类别。"""
        typecode = poi.get("typecode", "")
        typ = poi.get("type", "")

        # 按 typecode 前缀分类
        if typecode.startswith("060101"):
            return "保洁"
        if typecode.startswith("060100"):
            return "家政服务"
        if typecode.startswith("060102"):
            return "搬家"
        if typecode.startswith("060103"):
            return "管道疏通"
        if typecode.startswith("060104"):
            return "家电维修"
        if typecode.startswith("060107"):
            return "其他家政服务"

        # 按 type 文本关键词推测
        type_lower = typ.lower()
        if "保洁" in type_lower or "清洁" in type_lower:
            return "保洁"
        if "家政" in type_lower:
            return "家政服务"
        if "保姆" in type_lower or "月嫂" in type_lower:
            return "保姆月嫂"
        if "搬家" in type_lower:
            return "搬家"
        if "维修" in type_lower or "家电" in type_lower:
            return "家电维修"

        return "其他家政服务"
