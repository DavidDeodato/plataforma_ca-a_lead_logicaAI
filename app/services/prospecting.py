from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.services.firecrawl_client import FirecrawlClient


PHONE_RE = re.compile(r"(\+?\d[\d\-\(\)\s]{8,}\d)")
INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._-]+", re.IGNORECASE)
FACEBOOK_RE = re.compile(r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9._-]+", re.IGNORECASE)


@dataclass
class ProspectLead:
    business_name: str
    niche: str
    city: str
    source_url: str | None = None
    source_query: str | None = None
    source_platform: str | None = None
    website: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    phone_number: str | None = None
    notes: str | None = None


class ProspectingService:
    def __init__(self, *, validate_phone_format: bool = False) -> None:
        self.firecrawl = FirecrawlClient()
        self.validate_phone_format = validate_phone_format

    def find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        queries = [
            f'"{niche}" "{city}" whatsapp',
            f'"{niche}" "{city}" telefone',
            f'"{niche}" "{city}" contato',
            f'"{niche}" "{city}" site:instagram.com',
            f'"{niche}" "{city}" site:facebook.com',
            f'"{niche}" "{city}"',
        ]
        leads: list[ProspectLead] = []
        seen_keys: set[str] = set()

        per_query_limit = max(12, min(limit * 4, 30))
        for query in queries:
            results = self.firecrawl.search(query=query, limit=per_query_limit, location="Brazil")
            for result in results:
                lead = self._build_lead_from_result(result=result, niche=niche, city=city, source_query=query)
                if not self._has_contact_number(lead):
                    continue
                dedupe_key = self._dedupe_key(lead)
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                leads.append(lead)
                if len(leads) >= limit:
                    return leads
        return leads

    def _build_lead_from_result(
        self,
        *,
        result: dict,
        niche: str,
        city: str,
        source_query: str,
    ) -> ProspectLead:
        url = result.get("url")
        title = (result.get("title") or result.get("metadata", {}).get("title") or "").strip()
        description = (result.get("description") or "").strip()
        markdown = result.get("markdown") or ""
        raw_text = "\n".join([title, description, markdown])

        instagram_url = self._first_match(INSTAGRAM_RE, raw_text)
        facebook_url = self._first_match(FACEBOOK_RE, raw_text)
        phone_number = self.sanitize_phone(self._first_match(PHONE_RE, raw_text))
        source_platform = self._detect_platform(url)
        business_name = self._extract_business_name(title=title, url=url, niche=niche)

        website = None
        if url and "instagram.com" not in url and "facebook.com" not in url:
            website = url

        notes = description or None
        return ProspectLead(
            business_name=business_name,
            niche=niche,
            city=city,
            source_url=url,
            source_query=source_query,
            source_platform=source_platform,
            website=website,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            phone_number=phone_number,
            notes=notes,
        )

    @staticmethod
    def _extract_business_name(*, title: str, url: str | None, niche: str) -> str:
        if title:
            cleaned = title.split("|")[0].split("-")[0].strip()
            if cleaned:
                return cleaned[:255]
        if url:
            host = urlparse(url).netloc.replace("www.", "")
            return host[:255]
        return f"Lead {niche.title()}"

    @staticmethod
    def _first_match(pattern: re.Pattern[str], value: str) -> str | None:
        match = pattern.search(value)
        if not match:
            return None
        return match.group(0).strip()

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        if not digits:
            return None
        return digits

    def sanitize_phone(self, value: str | None) -> str | None:
        digits = self._normalize_phone(value)
        if not digits:
            return None
        if self.validate_phone_format and not self._is_valid_phone_format(digits):
            return None
        return digits

    @staticmethod
    def _detect_platform(url: str | None) -> str | None:
        if not url:
            return None
        if "instagram.com" in url:
            return "instagram"
        if "facebook.com" in url:
            return "facebook"
        return "web"

    @staticmethod
    def _has_contact_number(lead: ProspectLead) -> bool:
        return bool(lead.phone_number)

    @staticmethod
    def _is_valid_phone_format(value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        if not digits or digits.startswith("0"):
            return False

        if digits.startswith("55"):
            local_digits = digits[2:]
        else:
            local_digits = digits

        if len(local_digits) not in {10, 11}:
            return False

        ddd = local_digits[:2]
        subscriber = local_digits[2:]
        if len(ddd) != 2 or ddd.startswith("0"):
            return False
        if len(subscriber) not in {8, 9}:
            return False
        return True

    @staticmethod
    def _dedupe_key(lead: ProspectLead) -> str:
        if lead.phone_number:
            return lead.phone_number
        if lead.website:
            return lead.website
        if lead.instagram_url:
            return lead.instagram_url
        return f"{lead.business_name.lower()}::{lead.city.lower()}"
