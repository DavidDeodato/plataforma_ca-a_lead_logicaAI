from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentStrategy, Campaign, Conversation, KnowledgeItem, Lead, OfferProduct, Playbook, PromptTemplate, ProspectingRecipe
from app.services.conversion_kpis import recommended_action_snapshot, select_suggested_playbook


DEFAULT_PROMPTS = {
    "outreach": (
        "Voce escreve mensagens curtas de prospeccao via WhatsApp em portugues do Brasil. "
        "Nunca invente fatos. Nao use links na primeira mensagem. "
        "So personalize com fatos do contexto fornecido. Responda apenas com JSON: "
        '{"message":"...", "temperature":"cold", "stage":"contacted"}'
    ),
    "reply": (
        "Voce e um closer consultivo por WhatsApp. Use apenas fatos fornecidos. Nunca diga que e bot. "
        "Se o lead demonstrar interesse concreto, marque qualify=true. Responda apenas com JSON contendo: "
        '{"reply":"...", "temperature":"cold|warm|hot", "stage":"...", "qualify":true|false, '
        '"qualification_reason":"...", "handoff_summary":"...", '
        '"positive_reply_detected":true|false, '
        '"intent_status":"unknown|curious|interested|high_intent|objection|not_interested", '
        '"pain_status":"unknown|suspected|confirmed", '
        '"authority_status":"unknown|influencer|decision_maker|not_decision_maker", '
        '"urgency_status":"unknown|low|medium|high", '
        '"meeting_status":"not_offered|offered|booked|won|lost", '
        '"objection_status":"none|price|timing|already_has_solution|no_need|other"}'
    ),
    "followup": (
        "Escreva um follow-up curto de WhatsApp em portugues do Brasil. "
        'Sem parecer spam, sem links, sem inventar fatos. Responda apenas com JSON {"message":"..."}'
    ),
}


class StrategyResolverService:
    def resolve_snapshot(
        self,
        db: Session,
        *,
        phase: str,
        runtime: dict[str, Any],
        lead: Lead | None = None,
        conversation: Conversation | None = None,
        extra_instruction: str | None = None,
    ) -> dict[str, Any]:
        campaign = self._resolve_campaign(db, runtime=runtime, lead=lead)
        offer = self._resolve_offer(db, runtime=runtime, lead=lead, campaign=campaign)
        strategy = self._resolve_strategy(db, runtime=runtime, lead=lead, campaign=campaign)
        prompt_template = self._resolve_prompt_template(db, strategy=strategy, phase=phase)
        recipe = self._resolve_recipe(db, runtime=runtime, lead=lead, campaign=campaign)
        playbooks = self._resolve_playbooks(db, lead=lead, campaign=campaign)
        knowledge_items = self._resolve_knowledge(db, lead=lead, offer=offer, strategy=strategy)
        recommended_action = None
        suggested_playbook = None
        if lead:
            unread_count = conversation.unread_count if conversation else 0
            pending_human_review = bool(conversation.pending_human_review) if conversation else False
            recommended_action = recommended_action_snapshot(
                lead,
                unread_count=unread_count,
                pending_human_review=pending_human_review,
                has_open_conversation=conversation is not None,
            )
            suggested_playbook = select_suggested_playbook(lead, playbooks)

        return {
            "phase": phase,
            "campaign": self._campaign_payload(campaign),
            "offer": self._offer_payload(offer, runtime),
            "strategy": self._strategy_payload(strategy, runtime),
            "prompt_template": self._prompt_template_payload(prompt_template, phase),
            "prospecting_recipe": self._recipe_payload(recipe),
            "knowledge_items": [self._knowledge_payload(item) for item in knowledge_items],
            "recommended_action": recommended_action,
            "suggested_playbook": suggested_playbook,
            "extra_instruction": extra_instruction,
        }

    def render_instruction(self, snapshot: dict[str, Any], *, lead: Lead | None = None) -> str:
        offer = snapshot.get("offer") or {}
        strategy = snapshot.get("strategy") or {}
        campaign = snapshot.get("campaign") or {}
        prompt_template = snapshot.get("prompt_template") or {}
        knowledge_items = snapshot.get("knowledge_items") or []
        recommended_action = snapshot.get("recommended_action") or {}
        suggested_playbook = snapshot.get("suggested_playbook") or {}
        recipe = snapshot.get("prospecting_recipe") or {}

        offer_context = (
            f"Oferta principal: {offer.get('name')}. "
            f"Resumo da oferta: {offer.get('summary')}. "
            f"Objetivo comercial: {offer.get('objective')}. "
            f"CTA principal: {offer.get('cta_primary') or offer.get('cta_style') or ''}. "
        )
        strategy_context = (
            f"Estrategia ativa: {strategy.get('name') or 'default'}. "
            f"Persona: {strategy.get('persona') or 'consultor comercial'}. "
            f"Objetivo da estrategia: {strategy.get('primary_goal') or offer.get('objective')}. "
            f"Tom: {strategy.get('tone') or offer.get('sales_tone')}. "
            f"Abertura: {strategy.get('opening_strategy') or ''}. "
            f"Qualificacao: {strategy.get('qualification_strategy') or ''}. "
            f"Objeções: {strategy.get('objection_strategy') or ''}. "
            f"Handoff: {strategy.get('handoff_strategy') or ''}. "
            f"Guardrails: {strategy.get('guardrails') or ''}. "
        )
        campaign_context = ""
        if campaign.get("id"):
            campaign_context = (
                f"Campanha ligada: {campaign.get('name')}. Nicho: {campaign.get('niche')}. Cidade: {campaign.get('city')}. "
            )
        recipe_context = ""
        if recipe.get("id") or recipe.get("name"):
            recipe_context = (
                f"Receita de prospecção associada: {recipe.get('name') or 'custom'}. "
                f"Objetivo de aquisição: {recipe.get('objective') or ''}. "
            )
        prompt_context = ""
        if prompt_template.get("name") or prompt_template.get("instructions"):
            prompt_context = (
                f"Template da fase {snapshot.get('phase')}: {prompt_template.get('name') or 'default'}. "
                f"Instruções do template: {prompt_template.get('instructions') or ''}. "
            )
        knowledge_context = ""
        if knowledge_items:
            knowledge_context = "Conhecimento relevante: " + " | ".join(
                f"{item.get('category')} - {item.get('title')}: {item.get('content')}" for item in knowledge_items
            )
        lead_context = ""
        if lead:
            lead_context = (
                f"Lead: {lead.business_name}, nicho {lead.niche}, cidade {lead.city}, status {lead.status}, "
                f"estágio {lead.funnel_stage}, intenção {lead.intent_status}, dor {lead.pain_status}, "
                f"urgência {lead.urgency_status}, meeting {lead.meeting_status}, fit {lead.fit_score or 0}. "
            )
        action_context = ""
        if recommended_action:
            action_context = (
                f"Próxima ação sugerida: {recommended_action.get('label')}. {recommended_action.get('description') or ''} "
            )
        playbook_context = ""
        if suggested_playbook:
            playbook_context = (
                f"Playbook sugerido: {suggested_playbook.get('name')}. "
                f"Aplicabilidade: {suggested_playbook.get('applicability_reason')}. "
                f"Instruções: {suggested_playbook.get('instructions')}. "
                f"Objeções: {suggested_playbook.get('objection_handling') or ''}. "
                f"Qualificação: {suggested_playbook.get('qualification_rules') or ''}. "
            )
        extra_context = ""
        if snapshot.get("extra_instruction"):
            extra_context = f"Instrução adicional do operador: {snapshot['extra_instruction']}. "

        return (
            f"{offer_context}{strategy_context}{campaign_context}{recipe_context}"
            f"{prompt_context}{lead_context}{action_context}{playbook_context}{knowledge_context}{extra_context}"
        ).strip()

    def system_prompt_for_phase(self, snapshot: dict[str, Any]) -> str:
        prompt_template = snapshot.get("prompt_template") or {}
        return prompt_template.get("system_prompt") or DEFAULT_PROMPTS.get(snapshot.get("phase"), DEFAULT_PROMPTS["outreach"])

    def _resolve_campaign(self, db: Session, *, runtime: dict[str, Any], lead: Lead | None) -> Campaign | None:
        if lead and lead.campaign_id:
            campaign = db.get(Campaign, lead.campaign_id)
            if campaign:
                return campaign
        active = db.scalar(select(Campaign).where(Campaign.is_active.is_(True)).order_by(Campaign.updated_at.desc()))
        return active

    def _resolve_offer(
        self,
        db: Session,
        *,
        runtime: dict[str, Any],
        lead: Lead | None,
        campaign: Campaign | None,
    ) -> OfferProduct | None:
        offer_id = None
        if lead and lead.offer_product_id:
            offer_id = lead.offer_product_id
        elif campaign and campaign.offer_product_id:
            offer_id = campaign.offer_product_id
        else:
            offer_id = runtime.get("active_offer_product_id")
        return db.get(OfferProduct, int(offer_id)) if offer_id else None

    def _resolve_strategy(
        self,
        db: Session,
        *,
        runtime: dict[str, Any],
        lead: Lead | None,
        campaign: Campaign | None,
    ) -> AgentStrategy | None:
        strategy_id = None
        if lead and lead.agent_strategy_id:
            strategy_id = lead.agent_strategy_id
        elif campaign and campaign.agent_strategy_id:
            strategy_id = campaign.agent_strategy_id
        else:
            strategy_id = runtime.get("active_agent_strategy_id")
        return db.get(AgentStrategy, int(strategy_id)) if strategy_id else None

    def _resolve_recipe(
        self,
        db: Session,
        *,
        runtime: dict[str, Any],
        lead: Lead | None,
        campaign: Campaign | None,
    ) -> ProspectingRecipe | None:
        recipe_id = None
        if lead and lead.prospecting_recipe_id:
            recipe_id = lead.prospecting_recipe_id
        elif campaign and campaign.prospecting_recipe_id:
            recipe_id = campaign.prospecting_recipe_id
        else:
            recipe_id = runtime.get("active_prospecting_recipe_id")
        return db.get(ProspectingRecipe, int(recipe_id)) if recipe_id else None

    def _resolve_prompt_template(self, db: Session, *, strategy: AgentStrategy | None, phase: str) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(PromptTemplate.phase == phase, PromptTemplate.active.is_(True))
        if strategy:
            template = db.scalar(
                stmt.where(PromptTemplate.agent_strategy_id == strategy.id).order_by(PromptTemplate.updated_at.desc())
            )
            if template:
                return template
        return db.scalar(stmt.where(PromptTemplate.agent_strategy_id.is_(None)).order_by(PromptTemplate.updated_at.desc()))

    def _resolve_playbooks(self, db: Session, *, lead: Lead | None, campaign: Campaign | None) -> list[Playbook]:
        stmt = select(Playbook).where(Playbook.active.is_(True))
        niche = (lead.niche if lead else None) or (campaign.niche if campaign else None)
        if niche:
            items = list(
                db.scalars(
                    stmt.where((Playbook.niche == niche) | (Playbook.niche.is_(None))).order_by(Playbook.updated_at.desc())
                )
            )
            if items:
                return items
        return list(db.scalars(stmt.order_by(Playbook.updated_at.desc()).limit(8)))

    def _resolve_knowledge(
        self,
        db: Session,
        *,
        lead: Lead | None,
        offer: OfferProduct | None,
        strategy: AgentStrategy | None,
    ) -> list[KnowledgeItem]:
        stmt = select(KnowledgeItem).where(KnowledgeItem.active.is_(True))
        items = list(db.scalars(stmt.order_by(KnowledgeItem.updated_at.desc())))
        if not items:
            return []

        niche = (lead.niche if lead else None) or ""
        ranked: list[tuple[int, KnowledgeItem]] = []
        for item in items:
            score = 0
            if item.niche and niche and item.niche == niche:
                score += 4
            elif not item.niche:
                score += 1
            if offer and offer.name and item.title.lower() in offer.name.lower():
                score += 1
            if strategy and strategy.name and item.category.lower() in strategy.name.lower():
                score += 1
            ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked[:4]]

    @staticmethod
    def _campaign_payload(campaign: Campaign | None) -> dict[str, Any] | None:
        if not campaign:
            return None
        return {
            "id": campaign.id,
            "name": campaign.name,
            "niche": campaign.niche,
            "city": campaign.city,
            "status": campaign.status,
        }

    @staticmethod
    def _offer_payload(offer: OfferProduct | None, runtime: dict[str, Any]) -> dict[str, Any]:
        if offer:
            return {
                "id": offer.id,
                "name": offer.name,
                "summary": offer.summary,
                "objective": offer.objective,
                "target_customer": offer.target_customer,
                "pains": offer.pains,
                "differentiators": offer.differentiators,
                "proof_points": offer.proof_points,
                "cta_primary": offer.cta_primary,
                "allowed_claims": offer.allowed_claims,
                "forbidden_claims": offer.forbidden_claims,
            }
        return {
            "id": None,
            "name": runtime.get("offer_name"),
            "summary": runtime.get("offer_summary"),
            "objective": runtime.get("offer_goal"),
            "cta_style": runtime.get("cta_style"),
            "sales_tone": runtime.get("sales_tone"),
        }

    @staticmethod
    def _strategy_payload(strategy: AgentStrategy | None, runtime: dict[str, Any]) -> dict[str, Any]:
        if strategy:
            return {
                "id": strategy.id,
                "name": strategy.name,
                "persona": strategy.persona,
                "primary_goal": strategy.primary_goal,
                "tone": strategy.tone,
                "opening_strategy": strategy.opening_strategy,
                "qualification_strategy": strategy.qualification_strategy,
                "objection_strategy": strategy.objection_strategy,
                "follow_up_strategy": strategy.follow_up_strategy,
                "handoff_strategy": strategy.handoff_strategy,
                "guardrails": strategy.guardrails,
            }
        return {
            "id": None,
            "name": "Default",
            "persona": "closer consultivo",
            "primary_goal": runtime.get("offer_goal"),
            "tone": runtime.get("sales_tone"),
            "opening_strategy": runtime.get("cta_style"),
        }

    @staticmethod
    def _prompt_template_payload(prompt_template: PromptTemplate | None, phase: str) -> dict[str, Any]:
        if prompt_template:
            return {
                "id": prompt_template.id,
                "name": prompt_template.name,
                "phase": prompt_template.phase,
                "channel": prompt_template.channel,
                "system_prompt": prompt_template.system_prompt,
                "instructions": prompt_template.instructions,
                "output_contract": prompt_template.output_contract,
            }
        return {
            "id": None,
            "name": f"default_{phase}",
            "phase": phase,
            "channel": "whatsapp",
            "system_prompt": DEFAULT_PROMPTS.get(phase, DEFAULT_PROMPTS["outreach"]),
            "instructions": None,
            "output_contract": None,
        }

    @staticmethod
    def _recipe_payload(recipe: ProspectingRecipe | None) -> dict[str, Any] | None:
        if not recipe:
            return None
        return {
            "id": recipe.id,
            "name": recipe.name,
            "objective": recipe.objective,
            "source_channels": recipe.source_channels or [],
            "discovery_mode": recipe.discovery_mode,
            "minimum_valid_contacts": recipe.minimum_valid_contacts,
        }

    @staticmethod
    def _knowledge_payload(item: KnowledgeItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "title": item.title,
            "category": item.category,
            "content": item.content,
            "niche": item.niche,
        }
