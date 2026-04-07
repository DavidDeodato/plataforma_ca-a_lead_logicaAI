from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
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
    search_reason: str | None = None
    notes: str | None = None


class ProspectingService:
    def __init__(self, *, validate_phone_format: bool = False) -> None:
        self.firecrawl = FirecrawlClient()
        self.validate_phone_format = validate_phone_format

    def find_leads(self, niche: str, city: str, limit: int = 10, recipe: dict[str, Any] | None = None) -> list[ProspectLead]:
        effective_recipe = self._effective_recipe(recipe, limit=limit)
        leads: list[ProspectLead] = []
        seen_keys: set[str] = set()

        discovery_mode = str(effective_recipe.get("discovery_mode") or "search")
        if discovery_mode in {"agent", "hybrid"}:
            try:
                agent_leads = self._find_leads_via_agent(
                    niche=niche,
                    city=city,
                    recipe=effective_recipe,
                    limit=limit,
                )
                for lead in agent_leads:
                    if effective_recipe["require_phone"] and not self._has_contact_number(lead):
                        continue
                    dedupe_key = self._dedupe_key(lead)
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)
                    leads.append(lead)
                    if len(leads) >= limit:
                        return leads
            except Exception:
                if discovery_mode == "agent" and not effective_recipe.get("fallback_enabled", True):
                    raise

        queries = self._build_queries(niche=niche, city=city, recipe=effective_recipe)
        per_query_limit = max(12, min(int(effective_recipe["max_total_results"]) * 2, 40))
        for query in queries:
            results = self.firecrawl.search(query=query, limit=per_query_limit, location="Brazil")
            for result in results:
                lead = self._build_lead_from_result(result=result, niche=niche, city=city, source_query=query)
                if effective_recipe["require_phone"] and not self._has_contact_number(lead):
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
            search_reason=source_query,
            notes=notes,
        )

    def _effective_recipe(self, recipe: dict[str, Any] | None, *, limit: int) -> dict[str, Any]:
        base = {
            "objective": "",
            "system_prompt": "",
            "source_channels": ["google", "instagram", "facebook", "linkedin"],
            "inclusion_rules": "",
            "exclusion_rules": "",
            "minimum_valid_contacts": limit,
            "max_total_results": max(limit, 10),
            "search_depth": 2,
            "require_phone": True,
            "validate_phone_format": self.validate_phone_format,
            "discovery_mode": "search",
            "fallback_enabled": True,
            "agent_max_credits": None,
        }
        if recipe:
            base.update({key: value for key, value in recipe.items() if value is not None})
        return base

    def _build_queries(self, *, niche: str, city: str, recipe: dict[str, Any]) -> list[str]:
        queries: list[str] = []
        channels = [str(item).lower() for item in recipe.get("source_channels") or []]
        objective = str(recipe.get("objective") or "").strip()
        inclusion = str(recipe.get("inclusion_rules") or "").strip()

        base_terms = [
            f'"{niche}" "{city}" whatsapp',
            f'"{niche}" "{city}" telefone',
            f'"{niche}" "{city}" contato',
            f'"{niche}" "{city}"',
        ]
        if "linkedin" in channels or "posts" in channels:
            base_terms.append(f'"{niche}" "{city}" site:linkedin.com')
        if "instagram" in channels:
            base_terms.append(f'"{niche}" "{city}" site:instagram.com')
        if "facebook" in channels:
            base_terms.append(f'"{niche}" "{city}" site:facebook.com')
        if objective:
            base_terms.append(f'"{objective}" "{city}" telefone')
            base_terms.append(f'"{objective}" "{city}" whatsapp')
        if inclusion:
            base_terms.append(f'"{niche}" "{city}" "{inclusion}"')

        for query in base_terms:
            normalized = " ".join(query.split())
            if normalized not in queries:
                queries.append(normalized)
        return queries

    def _find_leads_via_agent(
        self,
        *,
        niche: str,
        city: str,
        recipe: dict[str, Any],
        limit: int,
    ) -> list[ProspectLead]:
        minimum_valid_contacts = int(recipe.get("minimum_valid_contacts") or limit)
        schema = {
            "type": "object",
            "properties": {
                "leads": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "business_name": {"type": "string"},
                            "source_url": {"type": "string"},
                            "website": {"type": ["string", "null"]},
                            "instagram_url": {"type": ["string", "null"]},
                            "facebook_url": {"type": ["string", "null"]},
                            "phone_number": {"type": ["string", "null"]},
                            "reason": {"type": "string"},
                        },
                        "required": ["business_name", "source_url", "phone_number", "reason"],
                    },
                }
            },
            "required": ["leads"],
        }
        prompt = self._build_agent_prompt(niche=niche, city=city, recipe=recipe, minimum_valid_contacts=minimum_valid_contacts)
        job_id = self.firecrawl.start_agent(
            prompt=prompt,
            schema=schema,
            strict_constrain_to_urls=False,
            max_credits=recipe.get("agent_max_credits"),
        )
        data = self.firecrawl.wait_for_agent(job_id, timeout_seconds=90)
        items = data.get("leads") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []

        leads: list[ProspectLead] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            phone_number = self.sanitize_phone(str(item.get("phone_number")) if item.get("phone_number") else None)
            lead = ProspectLead(
                business_name=str(item.get("business_name") or f"Lead {niche.title()}"),
                niche=niche,
                city=city,
                source_url=str(item.get("source_url")) if item.get("source_url") else None,
                source_query="agentic_recipe",
                source_platform=self._detect_platform(str(item.get("source_url")) if item.get("source_url") else None),
                website=str(item.get("website")) if item.get("website") else None,
                instagram_url=str(item.get("instagram_url")) if item.get("instagram_url") else None,
                facebook_url=str(item.get("facebook_url")) if item.get("facebook_url") else None,
                phone_number=phone_number,
                search_reason=str(item.get("reason") or ""),
                notes=str(item.get("reason") or ""),
            )
            leads.append(lead)
        return leads

    @staticmethod
    def _build_agent_prompt(*, niche: str, city: str, recipe: dict[str, Any], minimum_valid_contacts: int) -> str:
        channels = ", ".join(recipe.get("source_channels") or [])
        objective = recipe.get("objective") or f"achar {niche} em {city}"
        inclusion = recipe.get("inclusion_rules") or ""
        exclusion = recipe.get("exclusion_rules") or ""
        system_prompt = recipe.get("system_prompt") or ""
        return (
            f"Objetivo da pesquisa: {objective}. "
            f"Nicho alvo: {niche}. Cidade/regiao alvo: {city}. "
            f"Fontes priorizadas: {channels or 'busca web aberta'}. "
            f"Critérios de inclusão: {inclusion}. Critérios de exclusão: {exclusion}. "
            f"Continue procurando até conseguir pelo menos {minimum_valid_contacts} leads com telefone ou WhatsApp utilizável. "
            "Se um candidato parecer bom mas estiver sem telefone, continue a busca até achar contato válido ou substitua por outro lead melhor. "
            f"Instrução adicional da recipe: {system_prompt}."
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
