from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Conversation, Lead, Message, QualifiedLead


class ConversationAgentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.has_openai_credentials else None

    def draft_first_message(self, lead: Lead, research: dict[str, Any] | None = None, custom_instruction: str | None = None) -> str:
        default_text = (
            f"Oi, tudo bem? Vi o trabalho da {lead.business_name} e notei que talvez exista espaco para uma pagina "
            "mais focada em conversao. Se fizer sentido, posso te explicar em 2 minutos como eu estruturaria isso para o seu negocio."
        )
        if not self.client:
            return default_text

        system_prompt = (
            "Voce escreve mensagens curtas de prospeccao via WhatsApp em portugues do Brasil. "
            "Nunca invente fatos. Nao use links na primeira mensagem. "
            "So personalize com fatos do contexto fornecido. Responda apenas com JSON: "
            '{"message":"...", "temperature":"cold", "stage":"contacted"}'
        )
        user_prompt = {
            "lead": self._lead_snapshot(lead),
            "research": research or {},
            "custom_instruction": custom_instruction,
            "goal": "gerar primeira abordagem consultiva e natural",
        }
        payload = self._json_completion(system_prompt=system_prompt, user_payload=user_prompt)
        return payload.get("message") or default_text

    def handle_incoming_message(
        self,
        *,
        db: Session,
        lead: Lead,
        conversation: Conversation,
        inbound_text: str,
        research: dict[str, Any] | None = None,
        operating_instruction: str | None = None,
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
        }
        if not self.client:
            return default_reply

        system_prompt = (
            "Voce e um closer consultivo por WhatsApp vendendo landing pages para negocios locais. "
            "Use apenas fatos fornecidos. Nunca diga que e bot. "
            "Se o lead demonstrar interesse concreto, marque qualify=true. "
            "Responda apenas com JSON contendo: "
            '{"reply":"...", "temperature":"cold|warm|hot", "stage":"...", "qualify":true|false, '
            '"qualification_reason":"...", "handoff_summary":"..."}'
        )
        user_prompt = {
            "lead": self._lead_snapshot(lead),
            "research": research or {},
            "conversation": history,
            "inbound_text": inbound_text,
            "operating_instruction": operating_instruction,
            "goal": "continuar a conversa e avaliar qualificacao",
        }
        result = self._json_completion(system_prompt=system_prompt, user_payload=user_prompt)
        merged = {**default_reply, **result}

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
                lead.status = "qualified"
        return merged

    def schedule_followup_message(
        self,
        *,
        lead: Lead,
        conversation: Conversation,
        research: dict[str, Any] | None = None,
        operating_instruction: str | None = None,
    ) -> str:
        default_text = (
            f"Oi, passando so para retomar: faz sentido eu te mostrar uma ideia rapida de landing page "
            f"para a {lead.business_name}, pensando em gerar mais contatos?"
        )
        if not self.client:
            return default_text

        system_prompt = (
            "Escreva um follow-up curto de WhatsApp em portugues do Brasil. "
            "Sem parecer spam, sem links, sem inventar fatos. "
            'Responda apenas com JSON {"message":"..."}'
        )
        user_prompt = {
            "lead": self._lead_snapshot(lead),
            "research": research or {},
            "current_stage": conversation.stage,
            "temperature": conversation.temperature,
            "operating_instruction": operating_instruction,
        }
        result = self._json_completion(system_prompt=system_prompt, user_payload=user_prompt)
        return result.get("message") or default_text

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
