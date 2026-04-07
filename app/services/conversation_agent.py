from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Conversation, Lead, Message, QualifiedLead
from app.services.conversion_kpis import apply_inbound_signal, mark_manual_qualified
from app.services.runtime_config import RuntimeConfigService
from app.services.strategy_resolver import DEFAULT_PROMPTS, StrategyResolverService


class ConversationAgentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.has_openai_credentials else None

    def draft_first_message_payload(
        self,
        *,
        db: Session | None = None,
        lead: Lead,
        research: dict[str, Any] | None = None,
        custom_instruction: str | None = None,
    ) -> dict[str, Any]:
        default_text = (
            f"Oi, tudo bem? Vi o trabalho da {lead.business_name} e notei que talvez exista espaco para uma pagina "
            "mais focada em conversao. Se fizer sentido, posso te explicar em 2 minutos como eu estruturaria isso para o seu negocio."
        )
        snapshot = None
        runtime_instruction = custom_instruction
        system_prompt = DEFAULT_PROMPTS["outreach"]
        if db is not None:
            runtime_service = RuntimeConfigService()
            snapshot = runtime_service.build_instruction_snapshot(
                db,
                phase="outreach",
                lead=lead,
                conversation=None,
                extra_instruction=custom_instruction,
            )
            runtime_instruction = StrategyResolverService().render_instruction(snapshot, lead=lead)
            system_prompt = StrategyResolverService().system_prompt_for_phase(snapshot)
        if not self.client:
            return {"message": default_text, "temperature": "cold", "stage": "contacted", "_instruction_snapshot": snapshot}

        user_prompt = {
            "lead": self._lead_snapshot(lead),
            "research": research or {},
            "custom_instruction": runtime_instruction,
            "goal": "gerar primeira abordagem consultiva e natural",
        }
        payload = self._json_completion(system_prompt=system_prompt, user_payload=user_prompt)
        return {
            **payload,
            "message": payload.get("message") or default_text,
            "_instruction_snapshot": snapshot,
            "_prompt_phase": "outreach",
        }

    def draft_first_message(self, lead: Lead, research: dict[str, Any] | None = None, custom_instruction: str | None = None) -> str:
        payload = self.draft_first_message_payload(lead=lead, research=research, custom_instruction=custom_instruction)
        return str(payload.get("message") or "")

    def handle_incoming_message(
        self,
        *,
        db: Session,
        lead: Lead,
        conversation: Conversation,
        inbound_text: str,
        research: dict[str, Any] | None = None,
        operating_instruction: str | None = None,
        instruction_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        history = [
            {
                "direction": message.direction,
                "content": message.content,
                "status": message.status,
            }
            for message in conversation.messages[-12:]
        ]

        default_reply = {
            "reply": (
                f"Perfeito, {lead.business_name}. Posso te mandar uma sugestao objetiva de como eu faria uma landing page "
                "pensada para gerar mais contatos e conversoes para o seu negocio."
            ),
            "temperature": conversation.temperature or "warm",
            "stage": "engaged",
            "qualify": False,
            "qualification_reason": "",
            "handoff_summary": "",
            "positive_reply_detected": False,
            "intent_status": "unknown",
            "pain_status": "unknown",
            "authority_status": "unknown",
            "urgency_status": "unknown",
            "meeting_status": "not_offered",
            "objection_status": "none",
        }
        if not self.client:
            return {
                **default_reply,
                **apply_inbound_signal(lead, text=inbound_text),
                "_instruction_snapshot": instruction_snapshot,
                "_prompt_phase": "reply",
            }

        runtime_instruction = operating_instruction
        system_prompt = DEFAULT_PROMPTS["reply"]
        if instruction_snapshot:
            runtime_instruction = StrategyResolverService().render_instruction(instruction_snapshot, lead=lead)
            system_prompt = StrategyResolverService().system_prompt_for_phase(instruction_snapshot)
        user_prompt = {
            "lead": self._lead_snapshot(lead),
            "research": research or {},
            "conversation": history,
            "inbound_text": inbound_text,
            "operating_instruction": runtime_instruction,
            "goal": "continuar a conversa e avaliar qualificacao",
        }
        result = self._json_completion(system_prompt=system_prompt, user_payload=user_prompt)
        merged = {**default_reply, **result}
        signal_state = apply_inbound_signal(lead, text=inbound_text, signal_payload=merged)
        merged = {**merged, **signal_state}

        if merged.get("qualify"):
            existing = db.query(QualifiedLead).filter(QualifiedLead.lead_id == lead.id).one_or_none()
            if not existing:
                db.add(
                    QualifiedLead(
                        lead_id=lead.id,
                        score=0.85 if merged.get("temperature") == "hot" else 0.7,
                        qualification_reason=merged.get("qualification_reason") or "Interesse detectado em conversa.",
                        handoff_summary=merged.get("handoff_summary"),
                    )
                )
            mark_manual_qualified(lead)
        return {**merged, "_instruction_snapshot": instruction_snapshot, "_prompt_phase": "reply"}

    def schedule_followup_message_payload(
        self,
        *,
        db: Session | None = None,
        lead: Lead,
        conversation: Conversation,
        research: dict[str, Any] | None = None,
        operating_instruction: str | None = None,
    ) -> dict[str, Any]:
        default_text = (
            f"Oi, passando so para retomar: faz sentido eu te mostrar uma ideia rapida de landing page "
            f"para a {lead.business_name}, pensando em gerar mais contatos?"
        )
        snapshot = None
        runtime_instruction = operating_instruction
        system_prompt = DEFAULT_PROMPTS["followup"]
        if db is not None:
            runtime_service = RuntimeConfigService()
            snapshot = runtime_service.build_instruction_snapshot(
                db,
                phase="followup",
                lead=lead,
                conversation=conversation,
                extra_instruction=operating_instruction,
            )
            runtime_instruction = StrategyResolverService().render_instruction(snapshot, lead=lead)
            system_prompt = StrategyResolverService().system_prompt_for_phase(snapshot)
        if not self.client:
            return {"message": default_text, "_instruction_snapshot": snapshot, "_prompt_phase": "followup"}

        user_prompt = {
            "lead": self._lead_snapshot(lead),
            "research": research or {},
            "current_stage": conversation.stage,
            "temperature": conversation.temperature,
            "operating_instruction": runtime_instruction,
        }
        result = self._json_completion(system_prompt=system_prompt, user_payload=user_prompt)
        return {
            **result,
            "message": result.get("message") or default_text,
            "_instruction_snapshot": snapshot,
            "_prompt_phase": "followup",
        }

    def schedule_followup_message(
        self,
        *,
        lead: Lead,
        conversation: Conversation,
        research: dict[str, Any] | None = None,
        operating_instruction: str | None = None,
    ) -> str:
        payload = self.schedule_followup_message_payload(
            lead=lead,
            conversation=conversation,
            research=research,
            operating_instruction=operating_instruction,
        )
        return str(payload.get("message") or "")

    def _json_completion(self, *, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
            ],
        )
        output_text = getattr(response, "output_text", "") or ""
        if not output_text:
            return {}
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _lead_snapshot(lead: Lead) -> dict[str, Any]:
        return {
            "id": lead.id,
            "business_name": lead.business_name,
            "city": lead.city,
            "niche": lead.niche,
            "phone_number": lead.phone_number,
            "website": lead.website,
            "instagram_url": lead.instagram_url,
            "facebook_url": lead.facebook_url,
            "status": lead.status,
            "notes": lead.notes,
        }
