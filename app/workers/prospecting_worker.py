from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.db.models import Lead, LeadResearch
from app.services.enrichment import EnrichmentService
from app.services.prospecting import ProspectLead, ProspectingService


def run() -> None:
    settings = get_settings()
    init_db()

    prospecting_service = ProspectingService()
    enrichment_service = EnrichmentService()
    prospects = prospecting_service.find_leads(
        niche=settings.default_niche,
        city=settings.default_city,
        limit=settings.outreach_daily_limit,
    )

    with SessionLocal() as db:
        for prospect in prospects:
            lead = _upsert_lead(db=db, prospect=prospect)
            try:
                research = enrichment_service.enrich_lead(lead)
                db.add(
                    LeadResearch(
                        lead=lead,
                        source="firecrawl",
                        summary=research.get("summary"),
                        pain_points=research.get("pain_points"),
                        opportunities=research.get("opportunities"),
                        evidence=research.get("evidence"),
                        structured_data=research,
                    )
                )
                lead.website = lead.website or research.get("website")
                lead.instagram_url = lead.instagram_url or research.get("instagram_url")
                lead.phone_number = lead.phone_number or research.get("phone_number")
                lead.whatsapp_number = lead.whatsapp_number or research.get("phone_number")
            except Exception as exc:
                lead.notes = f"{lead.notes or ''}\nEnriquecimento falhou: {exc}".strip()
        db.commit()


def _upsert_lead(db, prospect: ProspectLead) -> Lead:
    lead = None
    if prospect.phone_number:
        lead = db.scalar(select(Lead).where(Lead.phone_number == prospect.phone_number))
    if not lead:
        lead = db.scalar(
            select(Lead).where(
                Lead.business_name == prospect.business_name,
                Lead.city == prospect.city,
            )
        )
    if not lead:
        lead = Lead(
            business_name=prospect.business_name,
            niche=prospect.niche,
            city=prospect.city,
        )
        db.add(lead)

    lead.phone_number = lead.phone_number or prospect.phone_number
    lead.whatsapp_number = lead.whatsapp_number or prospect.phone_number
    lead.website = lead.website or prospect.website
    lead.instagram_url = lead.instagram_url or prospect.instagram_url
    lead.facebook_url = lead.facebook_url or prospect.facebook_url
    lead.source_url = lead.source_url or prospect.source_url
    lead.source_query = prospect.source_query
    lead.source_platform = prospect.source_platform
    lead.notes = prospect.notes or lead.notes
    return lead


if __name__ == "__main__":
    run()
