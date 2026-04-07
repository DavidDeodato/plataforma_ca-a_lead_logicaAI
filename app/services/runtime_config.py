from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AppSetting, Conversation, Lead
from app.services.strategy_resolver import StrategyResolverService


RUNTIME_DEFAULTS = {
    "outbound_enabled": True,
    "auto_reply_enabled": False,
    "inbound_auto_reply_scope": "known_only",
    "persist_unknown_inbound": True,
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
    "active_offer_product_id": None,
    "active_agent_strategy_id": None,
    "active_prospecting_recipe_id": None,
}


class RuntimeConfigService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get_runtime_config(self, db: Session) -> dict[str, Any]:
        config = {
            "outbound_enabled": self.settings.outbound_enabled,
            "auto_reply_enabled": self.settings.auto_reply_enabled,
            "inbound_auto_reply_scope": RUNTIME_DEFAULTS["inbound_auto_reply_scope"],
            "persist_unknown_inbound": RUNTIME_DEFAULTS["persist_unknown_inbound"],
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
            "active_offer_product_id": RUNTIME_DEFAULTS["active_offer_product_id"],
            "active_agent_strategy_id": RUNTIME_DEFAULTS["active_agent_strategy_id"],
            "active_prospecting_recipe_id": RUNTIME_DEFAULTS["active_prospecting_recipe_id"],
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

    def build_instruction_snapshot(
        self,
        db: Session,
        *,
        phase: str,
        lead: Lead | None = None,
        conversation: Conversation | None = None,
        extra_instruction: str | None = None,
    ) -> dict[str, Any]:
        runtime = self.get_runtime_config(db)
        return StrategyResolverService().resolve_snapshot(
            db,
            phase=phase,
            runtime=runtime,
            lead=lead,
            conversation=conversation,
            extra_instruction=extra_instruction,
        )

    def build_sales_instruction(
        self,
        db: Session,
        *,
        lead: Lead | None = None,
        conversation: Conversation | None = None,
        phase: str = "outreach",
        extra_instruction: str | None = None,
    ) -> str:
        snapshot = self.build_instruction_snapshot(
            db,
            phase=phase,
            lead=lead,
            conversation=conversation,
            extra_instruction=extra_instruction,
        )
        return StrategyResolverService().render_instruction(snapshot, lead=lead)
