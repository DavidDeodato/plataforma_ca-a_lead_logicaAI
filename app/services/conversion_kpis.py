from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from typing import Any


FUNNEL_STAGES = [
    "captured",
    "contacted",
    "replied",
    "positive_reply",
    "pain_confirmed",
    "fit_confirmed",
    "meeting_offered",
    "meeting_booked",
    "qualified_opportunity",
    "closed_won",
    "closed_lost",
    "do_not_contact",
]

FUNNEL_STAGE_INDEX = {stage: index for index, stage in enumerate(FUNNEL_STAGES)}
TERMINAL_STAGES = {"closed_won", "closed_lost", "do_not_contact"}
INTENT_STATUSES = {"unknown", "curious", "interested", "high_intent", "objection", "not_interested"}
PAIN_STATUSES = {"unknown", "suspected", "confirmed"}
AUTHORITY_STATUSES = {"unknown", "influencer", "decision_maker", "not_decision_maker"}
URGENCY_STATUSES = {"unknown", "low", "medium", "high"}
MEETING_STATUSES = {"not_offered", "offered", "booked", "won", "lost"}
OBJECTION_STATUSES = {"none", "price", "timing", "already_has_solution", "no_need", "other"}
PRIORITY_LABELS = (
    (85, "agora"),
    (65, "alta"),
    (40, "media"),
    (0, "baixa"),
)

SERVICE_BUSINESS_KEYWORDS = {
    "barbearia",
    "barber",
    "clinica",
    "dentista",
    "odont",
    "adv",
    "advoc",
    "escritorio",
    "consult",
    "academia",
    "estetica",
    "salon",
    "salão",
    "imobili",
    "pet",
    "contab",
    "arquit",
    "medic",
    "fisi",
    "nutri",
    "psico",
    "agencia",
}

POSITIVE_REPLY_KEYWORDS = {
    "tenho interesse",
    "interesse",
    "quero",
    "pode mandar",
    "me manda",
    "me explique",
    "me explica",
    "como funciona",
    "quanto",
    "valor",
    "preco",
    "preço",
    "sim",
    "claro",
    "manda",
    "pode ser",
}

MEETING_BOOKED_KEYWORDS = {
    "agendar",
    "agenda",
    "reuniao",
    "reunião",
    "call",
    "ligacao",
    "ligação",
    "horario",
    "horário",
    "amanha",
    "amanhã",
}

PAIN_KEYWORDS = {
    "site",
    "pagina",
    "página",
    "landing",
    "lead",
    "conversao",
    "conversão",
    "agendamento",
    "whatsapp",
    "instagram",
    "vendas",
    "anuncio",
    "anúncio",
}

OBJECTION_KEYWORDS = {
    "price": {"caro", "preco", "preço", "valor alto", "sem verba", "sem orçamento", "sem orcamento"},
    "timing": {"depois", "agora nao", "agora não", "sem tempo", "mais tarde", "outro momento"},
    "already_has_solution": {"ja tenho", "já tenho", "tenho site", "tenho agencia", "tenho agência", "ja faço", "já faço"},
    "no_need": {"nao preciso", "não preciso", "sem interesse", "nao tenho interesse", "não tenho interesse"},
}


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().strip()


def contains_any(text: str, candidates: set[str]) -> bool:
    return any(token in text for token in candidates)


def normalize_choice(value: str | None, allowed: set[str], default: str) -> str:
    normalized = normalize_text(value).replace(" ", "_")
    if normalized in allowed:
        return normalized
    return default


def score_profile(
    *,
    business_name: str,
    niche: str | None,
    city: str | None,
    phone_number: str | None,
    whatsapp_number: str | None,
    website: str | None,
    instagram_url: str | None,
    facebook_url: str | None,
    notes: str | None,
    research_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_niche = normalize_text(niche)
    research_payload = research_payload or {}
    pain_points = [str(item) for item in research_payload.get("pain_points") or []]
    opportunities = [str(item) for item in research_payload.get("opportunities") or []]
    evidence = [str(item) for item in research_payload.get("evidence") or []]
    summary = str(research_payload.get("summary") or "")
    reasoning_blob = normalize_text(" ".join([summary, notes or "", *pain_points, *opportunities, *evidence]))

    components: list[dict[str, Any]] = []

    contact_score = 25 if (phone_number or whatsapp_number) else 0
    components.append(
        {
            "key": "contact_quality",
            "label": "qualidade do contato",
            "score": contact_score,
            "max_score": 25,
            "reason": "Tem telefone/WhatsApp acionável." if contact_score else "Ainda sem contato confiável.",
        }
    )

    icp_score = 10
    if normalized_niche and contains_any(normalized_niche, SERVICE_BUSINESS_KEYWORDS):
        icp_score = 25
    elif normalized_niche:
        icp_score = 16
    components.append(
        {
            "key": "icp_fit",
            "label": "aderência ao ICP",
            "score": icp_score,
            "max_score": 25,
            "reason": f"Nicho '{niche or 'não informado'}' comparado ao ICP de serviços locais.",
        }
    )

    digital_gap_score = 5 if website else 18
    if instagram_url and not website:
        digital_gap_score = 25
    components.append(
        {
            "key": "digital_gap",
            "label": "gap digital",
            "score": digital_gap_score,
            "max_score": 25,
            "reason": "Sem site principal e com presença social, indicando oportunidade clara de landing page."
            if digital_gap_score >= 18
            else "Já existe um site principal; ainda pode haver espaço, mas o gap é menor.",
        }
    )

    context_score = 0
    context_reasons: list[str] = []
    if summary:
        context_score += 6
        context_reasons.append("resumo salvo")
    if pain_points:
        context_score += 4
        context_reasons.append("dor mapeada")
    if opportunities:
        context_score += 3
        context_reasons.append("oportunidades mapeadas")
    if evidence:
        context_score += 2
        context_reasons.append("evidências")
    context_score = min(context_score, 15)
    components.append(
        {
            "key": "context_richness",
            "label": "riqueza de contexto",
            "score": context_score,
            "max_score": 15,
            "reason": ", ".join(context_reasons) if context_reasons else "Pouco contexto salvo para personalizar a abordagem.",
        }
    )

    pain_score = 5
    if contains_any(reasoning_blob, PAIN_KEYWORDS):
        pain_score = 10
    if (instagram_url or facebook_url) and not website:
        pain_score = max(pain_score, 8)
    components.append(
        {
            "key": "commercial_potential",
            "label": "potencial comercial",
            "score": pain_score,
            "max_score": 10,
            "reason": "Há sinais de dor/oportunidade ligados a conversão." if pain_score >= 8 else "Ainda faltam sinais fortes de dor.",
        }
    )

    total = round(sum(component["score"] for component in components), 1)
    label = "alto" if total >= 75 else "medio" if total >= 45 else "baixo"
    reasons = [component["reason"] for component in components if component["score"] > 0]
    return {
        "business_name": business_name,
        "score": total,
        "label": label,
        "components": components,
        "reasons": reasons,
        "scored_at": utcnow().isoformat(),
    }


def apply_fit_score_to_record(record: Any, research_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result = score_profile(
        business_name=getattr(record, "business_name", ""),
        niche=getattr(record, "niche", None),
        city=getattr(record, "city", None),
        phone_number=getattr(record, "phone_number", None),
        whatsapp_number=getattr(record, "whatsapp_number", None),
        website=getattr(record, "website", None),
        instagram_url=getattr(record, "instagram_url", None),
        facebook_url=getattr(record, "facebook_url", None),
        notes=getattr(record, "notes", None),
        research_payload=research_payload,
    )
    setattr(record, "fit_score", result["score"])
    setattr(record, "fit_label", result["label"])
    setattr(record, "fit_reasons_json", {"components": result["components"], "reasons": result["reasons"]})
    if hasattr(record, "fit_scored_at"):
        setattr(record, "fit_scored_at", utcnow())
    return result


def infer_signal_from_text(text: str | None) -> dict[str, Any]:
    normalized = normalize_text(text)
    objection_status = "none"
    for label, keywords in OBJECTION_KEYWORDS.items():
        if contains_any(normalized, keywords):
            objection_status = label
            break

    meeting_booked = contains_any(normalized, MEETING_BOOKED_KEYWORDS)
    positive_reply = contains_any(normalized, POSITIVE_REPLY_KEYWORDS) or meeting_booked

    if meeting_booked:
        intent_status = "high_intent"
        meeting_status = "booked"
        urgency_status = "high"
    elif positive_reply:
        intent_status = "interested"
        meeting_status = "not_offered"
        urgency_status = "medium"
    elif objection_status != "none":
        intent_status = "objection"
        meeting_status = "not_offered"
        urgency_status = "low"
    elif "?" in (text or ""):
        intent_status = "curious"
        meeting_status = "not_offered"
        urgency_status = "low"
    else:
        intent_status = "unknown"
        meeting_status = "not_offered"
        urgency_status = "unknown"

    pain_status = "confirmed" if contains_any(normalized, PAIN_KEYWORDS) else "unknown"
    return {
        "positive_reply_detected": positive_reply,
        "intent_status": intent_status,
        "pain_status": pain_status,
        "authority_status": "unknown",
        "urgency_status": urgency_status,
        "meeting_status": meeting_status,
        "objection_status": objection_status,
    }


def set_funnel_stage(lead: Any, stage: str, *, force: bool = False) -> str:
    if stage not in FUNNEL_STAGE_INDEX:
        return getattr(lead, "funnel_stage", "captured")
    current = getattr(lead, "funnel_stage", "captured") or "captured"
    if not force:
        if current in TERMINAL_STAGES and stage not in TERMINAL_STAGES:
            return current
        if FUNNEL_STAGE_INDEX[stage] < FUNNEL_STAGE_INDEX.get(current, 0):
            return current

    setattr(lead, "funnel_stage", stage)
    now = utcnow()
    stage_to_field = {
        "contacted": "first_contacted_at",
        "replied": "first_replied_at",
        "positive_reply": "positive_reply_at",
        "pain_confirmed": "pain_confirmed_at",
        "fit_confirmed": "fit_confirmed_at",
        "meeting_offered": "meeting_offered_at",
        "meeting_booked": "meeting_booked_at",
        "qualified_opportunity": "qualified_opportunity_at",
        "closed_won": "closed_won_at",
        "closed_lost": "closed_lost_at",
    }
    target_field = stage_to_field.get(stage)
    if target_field and not getattr(lead, target_field, None):
        setattr(lead, target_field, now)
    return stage


def apply_inbound_signal(
    lead: Any,
    *,
    text: str | None,
    signal_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = {**infer_signal_from_text(text), **(signal_payload or {})}
    merged["intent_status"] = normalize_choice(merged.get("intent_status"), INTENT_STATUSES, "unknown")
    merged["pain_status"] = normalize_choice(merged.get("pain_status"), PAIN_STATUSES, "unknown")
    merged["authority_status"] = normalize_choice(merged.get("authority_status"), AUTHORITY_STATUSES, "unknown")
    merged["urgency_status"] = normalize_choice(merged.get("urgency_status"), URGENCY_STATUSES, "unknown")
    merged["meeting_status"] = normalize_choice(merged.get("meeting_status"), MEETING_STATUSES, "not_offered")
    merged["objection_status"] = normalize_choice(merged.get("objection_status"), OBJECTION_STATUSES, "none")

    lead.intent_status = merged["intent_status"]
    lead.pain_status = merged["pain_status"]
    lead.authority_status = merged["authority_status"]
    lead.urgency_status = merged["urgency_status"]
    lead.meeting_status = merged["meeting_status"]
    lead.objection_status = merged["objection_status"]
    lead.last_signal_at = utcnow()

    set_funnel_stage(lead, "replied")
    if merged.get("positive_reply_detected"):
        lead.positive_reply_detected = True
        set_funnel_stage(lead, "positive_reply")
    if merged["pain_status"] == "confirmed":
        set_funnel_stage(lead, "pain_confirmed")
    if merged["intent_status"] in {"interested", "high_intent"}:
        set_funnel_stage(lead, "fit_confirmed")
    if merged["meeting_status"] == "offered":
        set_funnel_stage(lead, "meeting_offered")
    if merged["meeting_status"] == "booked":
        set_funnel_stage(lead, "meeting_booked")
    if merged["intent_status"] == "high_intent":
        set_funnel_stage(lead, "qualified_opportunity")
    if merged["intent_status"] == "not_interested":
        set_funnel_stage(lead, "closed_lost", force=True)
    return merged


def mark_contact_started(lead: Any) -> None:
    set_funnel_stage(lead, "contacted")
    if getattr(lead, "status", None) == "new":
        lead.status = "contacted"


def mark_manual_qualified(lead: Any) -> None:
    set_funnel_stage(lead, "qualified_opportunity")
    lead.meeting_status = "booked" if getattr(lead, "meeting_booked_at", None) else getattr(lead, "meeting_status", "not_offered")
    lead.status = "qualified"


def mark_disqualified(lead: Any) -> None:
    set_funnel_stage(lead, "do_not_contact", force=True)
    lead.meeting_status = "lost"
    lead.status = "do_not_contact"


def priority_snapshot(
    lead: Any,
    *,
    unread_count: int = 0,
    pending_human_review: bool = False,
) -> dict[str, Any]:
    fit_score = float(getattr(lead, "fit_score", 0) or 0)
    funnel_stage = getattr(lead, "funnel_stage", "captured") or "captured"
    intent_status = getattr(lead, "intent_status", "unknown") or "unknown"
    pain_status = getattr(lead, "pain_status", "unknown") or "unknown"
    meeting_status = getattr(lead, "meeting_status", "not_offered") or "not_offered"
    has_contact = bool(getattr(lead, "phone_number", None) or getattr(lead, "whatsapp_number", None))

    score = min(fit_score * 0.45, 45)
    reasons: list[str] = []

    stage_bonus_map = {
        "captured": 5,
        "contacted": 10,
        "replied": 18,
        "positive_reply": 28,
        "pain_confirmed": 34,
        "fit_confirmed": 40,
        "meeting_offered": 48,
        "meeting_booked": 55,
        "qualified_opportunity": 52,
        "closed_won": -10,
        "closed_lost": -55,
        "do_not_contact": -70,
    }
    stage_bonus = stage_bonus_map.get(funnel_stage, 0)
    score += stage_bonus
    if stage_bonus > 0:
        reasons.append(f"estágio {funnel_stage}")

    intent_bonus_map = {
        "unknown": 0,
        "curious": 8,
        "interested": 18,
        "high_intent": 30,
        "objection": 4,
        "not_interested": -35,
    }
    intent_bonus = intent_bonus_map.get(intent_status, 0)
    score += intent_bonus
    if intent_bonus > 0:
        reasons.append(f"intenção {intent_status}")
    elif intent_bonus < 0:
        reasons.append(f"intenção desfavorável: {intent_status}")

    if pain_status == "confirmed":
        score += 10
        reasons.append("dor confirmada")
    elif pain_status == "suspected":
        score += 4

    if meeting_status == "booked":
        score += 12
        reasons.append("reunião marcada")
    elif meeting_status == "offered":
        score += 7
        reasons.append("reunião ofertada")

    if has_contact:
        score += 8
    else:
        score -= 15
        reasons.append("sem contato forte")

    if unread_count > 0:
        score += min(unread_count * 4, 12)
        reasons.append("lead aguardando resposta")

    if pending_human_review:
        score += 10
        reasons.append("review humano pendente")

    final_score = max(0, min(round(score, 1), 100))
    label = next(priority for threshold, priority in PRIORITY_LABELS if final_score >= threshold)
    return {
        "score": final_score,
        "label": label,
        "reasons": reasons,
    }


def recommended_action_snapshot(
    lead: Any,
    *,
    unread_count: int = 0,
    pending_human_review: bool = False,
    has_open_conversation: bool = False,
) -> dict[str, Any]:
    funnel_stage = getattr(lead, "funnel_stage", "captured") or "captured"
    intent_status = getattr(lead, "intent_status", "unknown") or "unknown"
    pain_status = getattr(lead, "pain_status", "unknown") or "unknown"
    meeting_status = getattr(lead, "meeting_status", "not_offered") or "not_offered"
    objection_status = getattr(lead, "objection_status", "none") or "none"
    has_contact = bool(getattr(lead, "phone_number", None) or getattr(lead, "whatsapp_number", None))

    if pending_human_review:
        return {
            "key": "review_now",
            "label": "Revisar agora",
            "description": "O agente deixou rascunho pendente e essa thread precisa de decisão humana.",
            "tone": "warning",
        }
    if unread_count > 0:
        return {
            "key": "reply_now",
            "label": "Responder agora",
            "description": "Há mensagem nova do lead aguardando resposta.",
            "tone": "warning",
        }
    if not has_contact:
        return {
            "key": "fix_contact",
            "label": "Completar contato",
            "description": "Antes de qualquer outreach, falta telefone ou WhatsApp confiável.",
            "tone": "danger",
        }
    if meeting_status == "booked":
        return {
            "key": "handoff_meeting",
            "label": "Fazer handoff",
            "description": "A reunião já foi marcada; agora o foco é preparar o atendimento humano.",
            "tone": "success",
        }
    if intent_status == "high_intent" or funnel_stage in {"qualified_opportunity", "meeting_offered"}:
        return {
            "key": "ask_for_meeting",
            "label": "Pedir reunião",
            "description": "O lead já demonstra intenção forte; avance para uma próxima etapa concreta.",
            "tone": "success",
        }
    if objection_status != "none":
        return {
            "key": "handle_objection",
            "label": "Tratar objeção",
            "description": f"O último sinal forte foi objeção do tipo `{objection_status}`; vale responder com prova/contexto.",
            "tone": "warning",
        }
    if pain_status == "confirmed" or funnel_stage in {"pain_confirmed", "fit_confirmed"}:
        return {
            "key": "confirm_fit",
            "label": "Confirmar fit",
            "description": "A dor já apareceu; confirme contexto, urgência e se faz sentido avançar.",
            "tone": "info",
        }
    if has_open_conversation or funnel_stage in {"contacted", "replied", "positive_reply"}:
        return {
            "key": "continue_conversation",
            "label": "Continuar conversa",
            "description": "A thread já começou; o melhor passo é avançar contexto em vez de reiniciar a abordagem.",
            "tone": "info",
        }
    return {
        "key": "start_outreach",
        "label": "Iniciar outreach",
        "description": "Lead utilizável e ainda sem contato iniciado; vale abrir a conversa.",
        "tone": "default",
    }


def select_suggested_playbook(lead: Any, playbooks: list[Any] | None) -> dict[str, Any] | None:
    if not playbooks:
        return None

    lead_niche = (getattr(lead, "niche", None) or "").strip().lower()
    funnel_stage = (getattr(lead, "funnel_stage", None) or "").strip().lower()
    objection_status = (getattr(lead, "objection_status", None) or "").strip().lower()
    intent_status = (getattr(lead, "intent_status", None) or "").strip().lower()

    best_score = -1
    best_reason = ""
    best_playbook = None

    for playbook in playbooks:
        score = 0
        reasons: list[str] = []
        playbook_niche = (getattr(playbook, "niche", None) or "").strip().lower()
        playbook_stage = (getattr(playbook, "stage", None) or "").strip().lower()

        if playbook_niche and playbook_niche == lead_niche:
            score += 4
            reasons.append("nicho compatível")
        elif not playbook_niche:
            score += 1
            reasons.append("playbook geral")

        if playbook_stage and playbook_stage == funnel_stage:
            score += 5
            reasons.append("estágio compatível")
        elif not playbook_stage:
            score += 1

        if objection_status != "none" and getattr(playbook, "objection_handling", None):
            score += 2
            reasons.append("tem tratamento de objeção")

        if intent_status in {"interested", "high_intent"} and getattr(playbook, "qualification_rules", None):
            score += 2
            reasons.append("tem regra de qualificação")

        if score > best_score:
            best_score = score
            best_reason = ", ".join(reasons) if reasons else "melhor aderência geral"
            best_playbook = playbook

    if not best_playbook:
        return None
    return {
        "id": best_playbook.id,
        "name": best_playbook.name,
        "niche": best_playbook.niche,
        "stage": best_playbook.stage,
        "instructions": best_playbook.instructions,
        "objection_handling": best_playbook.objection_handling,
        "qualification_rules": best_playbook.qualification_rules,
        "applicability_reason": best_reason,
    }
