from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AppSetting, Campaign, KnowledgeItem, Playbook


RUNTIME_DEFAULTS = {
    "outbound_enabled": True,
    "auto_reply_enabled": False,
    "default_niche": None,
    "default_city": None,
    "outreach_daily_limit": None,
    "outreach_delay_seconds": None,
    "default_auto_reply_delay_seconds": 30,
    "offer_name": "landing page",
    "offer_summary": "uma landing page focada em conversao para captar mais contatos qualificados",
    "offer_goal": "gerar mais contatos, agendamentos e vendas",
    "sales_tone": "consultivo, humano e objetivo",
    "cta_style": "convidar o lead para entender rapidamente como a pagina ajudaria o negocio",
}


class RuntimeConfigService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get_runtime_config(self, db: Session) -> dict[str, Any]:
        config = {
            "outbound_enabled": self.settings.outbound_enabled,
            "auto_reply_enabled": self.settings.auto_reply_enabled,
            "default_niche": self.settings.default_niche,
            "default_city": self.settings.default_city,
            "outreach_daily_limit": self.settings.outreach_daily_limit,
            "outreach_delay_seconds": self.settings.outreach_delay_seconds,
            "default_auto_reply_delay_seconds": RUNTIME_DEFAULTS["default_auto_reply_delay_seconds"],
            "offer_name": RUNTIME_DEFAULTS["offer_name"],
            "offer_summary": RUNTIME_DEFAULTS["offer_summary"],
            "offer_goal": RUNTIME_DEFAULTS["offer_goal"],
            "sales_tone": RUNTIME_DEFAULTS["sales_tone"],
            "cta_style": RUNTIME_DEFAULTS["cta_style"],
        }

        rows = list(db.scalars(select(AppSetting)))
        for row in rows:
            config[row.key] = row.value_json
        return config

    def update_runtime_config(self, db: Session, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_runtime_config(db)
        for key, value in updates.items():
            if value is None:
                continue
            setting = db.scalar(select(AppSetting).where(AppSetting.key == key))
            if not setting:
                setting = AppSetting(key=key, value_json=value)
                db.add(setting)
            else:
                setting.value_json = value
            current[key] = value
        db.commit()
        return current

    def get_flags(self, db: Session) -> dict[str, bool]:
        config = self.get_runtime_config(db)
        return {
            "outbound_enabled": bool(config["outbound_enabled"]),
            "auto_reply_enabled": bool(config["auto_reply_enabled"]),
        }

    def build_sales_instruction(self, db: Session) -> str:
        config = self.get_runtime_config(db)
        active_campaign = db.scalar(select(Campaign).where(Campaign.is_active.is_(True)).order_by(Campaign.updated_at.desc()))
        playbooks = list(db.scalars(select(Playbook).where(Playbook.active.is_(True)).order_by(Playbook.updated_at.desc()).limit(5)))
        knowledge_items = list(
            db.scalars(select(KnowledgeItem).where(KnowledgeItem.active.is_(True)).order_by(KnowledgeItem.updated_at.desc()).limit(8))
        )

        campaign_context = ""
        if active_campaign:
            campaign_context = (
                f" Campanha ativa: {active_campaign.name}. Nicho: {active_campaign.niche}. Cidade: {active_campaign.city}. "
                f"Oferta: {active_campaign.offer_name}. Objetivo: {active_campaign.offer_goal}. "
                f"Tom: {active_campaign.sales_tone}. CTA: {active_campaign.cta_style}."
            )

        playbook_context = ""
        if playbooks:
            playbook_context = " Playbooks ativos: " + " | ".join(
                f"{item.name}: {item.instructions}" for item in playbooks
            )

        knowledge_context = ""
        if knowledge_items:
            knowledge_context = " Conhecimento relevante: " + " | ".join(
                f"{item.category} - {item.title}: {item.content}" for item in knowledge_items
            )

        return (
            f"Oferta principal: {config['offer_name']}. "
            f"Resumo da oferta: {config['offer_summary']}. "
            f"Objetivo comercial: {config['offer_goal']}. "
            f"Tom desejado: {config['sales_tone']}. "
            f"Estilo de CTA: {config['cta_style']}."
            f"{campaign_context}{playbook_context}{knowledge_context}"
        )
