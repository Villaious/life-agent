import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class BookingContentDecomposerAgent:
    SERVICE_TERMS = [
        "上门保洁",
        "家庭保洁",
        "深度保洁",
        "日常保洁",
        "保洁",
        "打扫",
        "家电维修",
        "管道疏通",
        "维修",
        "修理",
        "美甲",
        "美容",
        "美发",
        "搬家",
    ]

    PROVINCES = [
        "北京",
        "上海",
        "天津",
        "重庆",
        "河北",
        "山西",
        "辽宁",
        "吉林",
        "黑龙江",
        "江苏",
        "浙江",
        "安徽",
        "福建",
        "江西",
        "山东",
        "河南",
        "湖北",
        "湖南",
        "广东",
        "海南",
        "四川",
        "贵州",
        "云南",
        "陕西",
        "甘肃",
        "青海",
        "台湾",
        "内蒙古",
        "广西",
        "西藏",
        "宁夏",
        "新疆",
        "香港",
        "澳门",
    ]

    LOCATION_SUFFIXES = (
        "大学",
        "学院",
        "学校",
        "医院",
        "小区",
        "大厦",
        "广场",
        "商场",
        "园区",
        "科技园",
        "机场",
        "车站",
        "火车站",
        "高铁站",
        "区",
        "县",
        "镇",
        "街道",
    )

    def __init__(self, timezone: str = "Asia/Hong_Kong") -> None:
        self.timezone = timezone

    def decompose(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        current = now or datetime.now(self._timezone())
        event = self._extract_event(text)
        return {
            "raw_text": text,
            "event": event,
            "service_category": self._guess_category(event or text),
            "location": context.get("location") or self._extract_location(text),
            "time_preference": context.get("time_preference") or self._extract_time(text, current),
        }

    def _extract_event(self, text: str) -> str | None:
        for term in self.SERVICE_TERMS:
            if term in text:
                return term
        return None

    def _guess_category(self, text: str) -> str:
        if any(term in text for term in ["保洁", "打扫", "清洁", "家政"]):
            return "home_cleaning"
        if any(term in text for term in ["维修", "修理", "管道", "家电"]):
            return "repair"
        if any(term in text for term in ["美甲", "美容", "美发"]):
            return "beauty"
        if "搬家" in text:
            return "moving"
        return "unknown"

    def _extract_time(self, text: str, now: datetime) -> str | None:
        date_value = self._resolve_date(text, now)
        part = self._resolve_day_part(text)

        if not date_value and not part:
            return None
        if not date_value:
            date_value = now.date()

        date_text = date_value.isoformat()
        return f"{date_text} {part}" if part else date_text

    def _resolve_date(self, text: str, now: datetime):
        if "今天" in text or "今晚" in text:
            return now.date()
        if "大后天" in text:
            return (now + timedelta(days=3)).date()
        if "明天" in text:
            return (now + timedelta(days=1)).date()
        if "后天" in text:
            return (now + timedelta(days=2)).date()

        month_day = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", text)
        if month_day:
            month = int(month_day.group(1))
            day = int(month_day.group(2))
            return now.replace(month=month, day=day).date()

        weekday_match = re.search(r"(?:周|星期)([一二三四五六日天])", text)
        if weekday_match:
            target = "一二三四五六日天".index(weekday_match.group(1)) % 7
            current = now.weekday()
            delta = (target - current) % 7
            if delta == 0:
                delta = 7
            return (now + timedelta(days=delta)).date()

        return None

    def _resolve_day_part(self, text: str) -> str | None:
        if "凌晨" in text:
            return "凌晨"
        if "早上" in text or "上午" in text:
            return "上午"
        if "中午" in text:
            return "中午"
        if "下午" in text:
            return "下午"
        if "晚上" in text or "今晚" in text:
            return "晚上"

        hour = re.search(r"(\d{1,2})\s*[点:：]\s*(\d{1,2})?", text)
        if hour:
            minutes = hour.group(2) or "00"
            return f"{int(hour.group(1)):02d}:{int(minutes):02d}"
        return None

    def _extract_location(self, text: str) -> str | None:
        cleaned = self._normalize_for_location(text)
        if not cleaned:
            return None

        for extractor in (
            self._extract_suffix_location,
            self._extract_province_city_location,
            self._extract_preposition_location,
            self._extract_remaining_location,
        ):
            location = extractor(cleaned)
            if self._is_valid_location(location):
                return location
        return None

    def _extract_suffix_location(self, text: str) -> str | None:
        suffix_pattern = "|".join(sorted(map(re.escape, self.LOCATION_SUFFIXES), key=len, reverse=True))
        match = re.search(rf"([\u4e00-\u9fa5]{{2,24}}(?:{suffix_pattern}))", text)
        return match.group(1) if match else None

    def _extract_province_city_location(self, text: str) -> str | None:
        province_pattern = "|".join(map(re.escape, self.PROVINCES))
        match = re.search(rf"({province_pattern})(?:省|市|自治区|特别行政区)?([\u4e00-\u9fa5]{{2,8}}?)(?:市|区|县)?(?:的|附近|周边|$)", text)
        if not match:
            return None
        province = match.group(1)
        city = self._trim_location_tail(match.group(2))
        if city:
            return f"{province}{city}"
        return province

    def _extract_preposition_location(self, text: str) -> str | None:
        match = re.search(r"(?:在|到|去)([\u4e00-\u9fa5A-Za-z0-9\s-]{2,32}?)(?:的|附近|周边|预约|订|找|安排|$)", text)
        if not match:
            return None
        return self._trim_location_tail(match.group(1))

    def _extract_remaining_location(self, text: str) -> str | None:
        candidate = self._trim_location_tail(text)
        if 2 <= len(candidate) <= 24:
            return candidate
        return None

    def _normalize_for_location(self, text: str) -> str:
        cleaned = self._remove_time_words(text)
        cleaned = self._remove_service_words(cleaned)
        cleaned = re.sub(r"(帮我|请帮我|麻烦|预约|预定|订|下单|找|安排|需要|想要|一个|一下|上门)", "", cleaned)
        cleaned = re.sub(r"[，。,.!?！？；;、]", " ", cleaned)
        cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned.strip("的在到去")

    def _remove_service_words(self, text: str) -> str:
        cleaned = text
        for term in sorted(self.SERVICE_TERMS, key=len, reverse=True):
            cleaned = cleaned.replace(term, "")
        return cleaned

    def _remove_time_words(self, text: str) -> str:
        patterns = [
            r"今天|今晚|明天|后天|大后天",
            r"(?:周|星期)[一二三四五六日天]",
            r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]?",
            r"凌晨|早上|上午|中午|下午|晚上",
            r"\d{1,2}\s*[点:：]\s*\d{0,2}",
        ]
        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned)
        return cleaned

    def _trim_location_tail(self, value: str | None) -> str | None:
        if not value:
            return None
        location = value.strip(" 的在到去附近周边")
        for term in ["预约", "预定", "订", "下单", "找", "安排", "需要", "想要"]:
            if term in location:
                location = location.split(term, 1)[0]
        for service in sorted(self.SERVICE_TERMS, key=len, reverse=True):
            location = location.replace(service, "")
        return location.strip(" 的在到去附近周边")

    def _is_valid_location(self, value: str | None) -> bool:
        if not value or len(value) < 2:
            return False
        if any(term == value for term in self.SERVICE_TERMS):
            return False
        if value in {"帮我", "请帮我", "预约", "预定", "安排", "需要", "想要"}:
            return False
        if any(service in value for service in self.SERVICE_TERMS) and len(value) <= 6:
            return False
        return True

    def _timezone(self):
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=8))
