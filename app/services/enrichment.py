from __future__ import annotations

from typing import Any

from app.db.models import Lead
from app.services.firecrawl_client import FirecrawlClient


LEAD_RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "business_name": {"type": "string"},
        "city": {"type": "string"},
        "services": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "pain_points": {"type": "array", "items": {"type": "string"}},
        "opportunities": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "suggested_pitch_angle": {"type": "string"},
        "phone_number": {"type": "string"},
        "instagram_url": {"type": "string"},
        "website": {"type": "string"},
    },
    "required": ["summary", "pain_points", "opportunities", "evidence", "suggested_pitch_angle"],
}


class EnrichmentService:
    def __init__(self) -> None:
        self.firecrawl = FirecrawlClient()

    def enrich_lead(self, lead: Lead) -> dict[str, Any]:
        prompt = self._build_prompt(lead)
        urls = [candidate for candidate in [lead.website, lead.instagram_url, lead.facebook_url, lead.source_url] if candidate]

        if urls:
            try:
                extract_result = self.firecrawl.extract(
                    urls=urls[:3],
                    prompt=prompt,
                    schema=LEAD_RESEARCH_SCHEMA,
                    enable_web_search=True,
                )
                data = extract_result.get("data")
                if data:
                    return data
            except Exception:
                # Se extract falhar, cai para o agent.
                pass

        job_id = self.firecrawl.start_agent(
            prompt=prompt,
            urls=urls[:3] or None,
            schema=LEAD_RESEARCH_SCHEMA,
            strict_constrain_to_urls=bool(urls),
        )
        return self.firecrawl.wait_for_agent(job_id)

    @staticmethod
    def _build_prompt(lead: Lead) -> str:
        references = ", ".join(filter(None, [lead.business_name, lead.city, lead.website, lead.instagram_url, lead.facebook_url]))
        return (
            "Pesquise o negocio abaixo e monte um resumo comercial para prospeccao de landing page. "
            "Quero fatos observaveis, dores provaveis com base no que aparece online, oportunidades de conversao "
            "e um angulo de abordagem consultiva. "
            f"Negocio de referencia: {references}."
        )
