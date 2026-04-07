from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_management.db"
os.environ["OUTBOUND_ENABLED"] = "false"
os.environ["AUTO_REPLY_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["WASENDER_API_KEY"] = ""

from app.core.database import Base, engine
from app.core.config import get_settings
from app.main import app
from app.services.prospecting import ProspectLead


@pytest.fixture
def client() -> TestClient:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def _create_lead(client: TestClient, *, business_name: str = "Clinica Alfa", phone_number: str = "+5527999911111") -> int:
    response = client.post(
        "/api/leads",
        json={
            "business_name": business_name,
            "niche": "clinica odontologica",
            "city": "Vitoria, ES",
            "phone_number": phone_number,
            "instagram_url": "https://instagram.com/clinicaalfa",
        },
    )
    return response.json()["id"]


def test_runtime_settings_roundtrip(client: TestClient) -> None:
    get_response = client.get("/api/settings/runtime")
    assert get_response.status_code == 200
    assert get_response.json()["outbound_enabled"] is False

    patch_response = client.patch(
        "/api/settings/runtime",
        json={
            "offer_name": "pagina de vendas",
            "offer_goal": "gerar mais agendamentos",
            "sales_tone": "consultivo",
        },
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["offer_name"] == "pagina de vendas"
    assert payload["offer_goal"] == "gerar mais agendamentos"
    assert "default_auto_reply_delay_seconds" in payload
    assert payload["inbound_auto_reply_scope"] == "known_only"
    assert payload["persist_unknown_inbound"] is True


def test_dashboard_summary(client: TestClient) -> None:
    _create_lead(client)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["leads"] >= 1
    assert payload["safe_mode"]["outbound_enabled"] is False
    assert "conversion" in payload
    assert "funnel" in payload
    assert "campaigns" in payload
    assert "offers" in payload
    assert "strategies" in payload
    assert "recipes" in payload
    assert payload["conversion"]["lead_fit_score_avg"] >= 0


def test_modular_entities_link_campaign_and_saved_lead(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module

    offer = client.post(
        "/api/offer-products",
        json={
            "name": "Landing page modular",
            "summary": "LP com foco em reuniões",
            "objective": "agendar mais calls qualificadas",
        },
    ).json()
    strategy = client.post(
        "/api/agent-strategies",
        json={
            "name": "SDR consultivo",
            "persona": "SDR senior",
            "primary_goal": "abrir diagnóstico rápido",
        },
    ).json()
    recipe = client.post(
        "/api/prospecting-recipes",
        json={
            "name": "Recipe clay-like",
            "objective": "achar leads quentes",
            "system_prompt": "continuar até achar contatos válidos",
            "source_channels": ["google", "linkedin"],
            "minimum_valid_contacts": 1,
            "max_total_results": 5,
            "search_depth": 2,
            "require_phone": True,
            "validate_phone_format": False,
            "discovery_mode": "hybrid",
            "fallback_enabled": True,
            "active": True,
        },
    ).json()
    prompt_category = client.post(
        "/api/prospecting-prompt-categories",
        json={
            "name": "Vender landing page para clinicas",
            "description": "Testes de aquisição para clínicas com necessidade de captação.",
            "offer_context": "Landing page focada em agendamento de avaliações.",
            "target_niche": "clinica odontologica",
        },
    ).json()
    prompt = client.post(
        "/api/prospecting-prompts",
        json={
            "category_id": prompt_category["id"],
            "name": "Clinica com sinal de compra recente",
            "prompt_text": "Ache clínicas com sinal recente de necessidade comercial em {{city}}.",
            "objective": "encontrar clinicas com urgência de captar mais pacientes",
            "source_channels": ["google", "linkedin"],
            "discovery_mode": "hybrid",
            "minimum_valid_contacts": 1,
            "require_phone": True,
            "fallback_enabled": True,
            "search_depth": 2,
            "agent_max_credits": 200,
            "notes": "Usar quando quiser rapidez com tese validada.",
        },
    ).json()

    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Campanha Modular",
            "status": "active",
            "niche": "clinica odontologica",
            "city": "Vitoria, ES",
            "offer_product_id": offer["id"],
            "agent_strategy_id": strategy["id"],
            "prospecting_recipe_id": recipe["id"],
            "offer_name": "landing page modular",
            "offer_summary": "lp para converter pacientes",
            "offer_goal": "agendar mais avaliações",
            "sales_tone": "consultivo",
            "cta_style": "pedir reunião curta",
            "auto_reply_enabled": False,
            "reply_delay_seconds": 30,
            "start_outreach_on_approve": False,
            "is_active": True,
        },
    ).json()

    def fake_find_leads(self, niche: str, city: str, limit: int = 10, recipe: dict | None = None) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Lead Modular",
                niche=niche,
                city=city,
                phone_number="+5527999988888",
                source_url="https://example.com/lead-modular",
                source_platform="web",
                search_reason="sinal forte de compra em vaga e página institucional",
            )
        ]

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)

    batch_response = client.post(
        "/api/prospecting/batches/preview",
        json={
            "niche": "clinica odontologica",
            "city": "Vitoria, ES",
            "limit": 1,
            "enrich": False,
            "validate_phone_format": False,
            "campaign_id": campaign["id"],
            "prompt_category_id": prompt_category["id"],
            "prompt_id": prompt["id"],
        },
    )
    assert batch_response.status_code == 200
    batch_payload = batch_response.json()
    assert batch_payload["recipe_id"] == recipe["id"]
    assert batch_payload["prompt_id"] == prompt["id"]
    assert batch_payload["prompt_category_id"] == prompt_category["id"]
    assert batch_payload["prompt_snapshot_json"]["name"] == prompt["name"]
    assert batch_payload["search_metrics_json"]["discovery_mode"] == "hybrid"
    assert batch_payload["search_metrics_json"]["prompt_name"] == prompt["name"]
    assert batch_payload["candidates"][0]["search_reason"]
    assert batch_payload["candidates"][0]["prospecting_prompt_id"] == prompt["id"]

    applied = client.post(
        f"/api/prospecting/batches/{batch_payload['id']}/apply",
        json={"candidate_ids": [batch_payload["candidates"][0]["id"]], "action": "save_only"},
    )
    assert applied.status_code == 200
    saved_candidate = applied.json()["candidates"][0]
    assert saved_candidate["lead_id"] is not None

    lead_detail = client.get(f"/api/leads/{saved_candidate['lead_id']}").json()
    assert lead_detail["offer_product_id"] == offer["id"]
    assert lead_detail["agent_strategy_id"] == strategy["id"]
    assert lead_detail["prospecting_recipe_id"] == recipe["id"]
    assert lead_detail["prospecting_prompt_category_id"] == prompt_category["id"]
    assert lead_detail["prospecting_prompt_id"] == prompt["id"]
    assert lead_detail["source_origin"] == "prospecting"

    summary = client.get("/api/dashboard/summary").json()
    assert any(item["name"] == "Landing page modular" for item in summary["offers"])
    assert any(item["name"] == "SDR consultivo" for item in summary["strategies"])
    assert any(item["name"] == "Recipe clay-like" for item in summary["recipes"])
    assert any(item["name"] == prompt_category["name"] for item in summary["prompt_categories"])
    assert any(item["name"] == prompt["name"] for item in summary["prospecting_prompts"])


def test_unknown_inbound_is_persisted_but_not_auto_replied_when_scope_is_known_only(client: TestClient) -> None:
    client.patch(
        "/api/settings/runtime",
        json={
            "auto_reply_enabled": True,
            "inbound_auto_reply_scope": "known_only",
            "persist_unknown_inbound": True,
        },
    )

    webhook_response = client.post(
        "/webhooks/wasender",
        json={
            "event": "messages.received",
            "data": {
                "messages": {
                    "key": {
                        "id": "unknown-inbound-1",
                        "fromMe": False,
                        "remoteJid": "5527999919900@s.whatsapp.net",
                        "cleanedSenderPn": "+5527999919900",
                    },
                    "messageBody": "oi, quero entender melhor",
                    "message": {"conversation": "oi, quero entender melhor"},
                }
            },
        },
    )
    assert webhook_response.status_code == 200

    conversations = client.get("/api/conversations").json()["items"]
    assert conversations[0]["inbound_unverified"] is True
    assert conversations[0]["source_origin"] == "inbound_unknown"

    tasks = client.get("/api/tasks").json()["items"]
    delayed_auto_reply_tasks = [task for task in tasks if task["task_type"] == "delayed_auto_reply"]
    assert delayed_auto_reply_tasks == []


def test_lead_search_and_detail(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Studio Beta", phone_number="+5527999922222")

    search_response = client.get("/api/leads/search", params={"q": "Studio"})
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["total"] >= 1
    assert any(item["business_name"] == "Studio Beta" for item in search_payload["items"])

    detail_response = client.get(f"/api/leads/{lead_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == lead_id
    assert detail_payload["research_entries"] == []
    assert detail_payload["fit_score"] is not None
    assert detail_payload["funnel_stage"] == "captured"


def test_manual_qualification_and_disqualification(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Barbearia Zeta", phone_number="+5527999933333")

    qualify_response = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={
            "score": 0.9,
            "qualification_reason": "Demonstrou interesse real",
            "handoff_summary": "Pedir proposta comercial",
        },
    )
    assert qualify_response.status_code == 200
    qualified_payload = qualify_response.json()
    assert qualified_payload["status"] == "qualified"
    assert qualified_payload["funnel_stage"] == "qualified_opportunity"
    assert qualified_payload["qualified_lead"]["score"] == 0.9

    disqualify_response = client.post(f"/api/leads/{lead_id}/disqualify")
    assert disqualify_response.status_code == 200
    assert disqualify_response.json()["status"] == "do_not_contact"
    assert disqualify_response.json()["funnel_stage"] == "do_not_contact"


def test_prospecting_candidates_and_conversations_expose_fit_and_stage_kpis(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Lead Fit Prospectado",
                niche=niche,
                city=city,
                phone_number="+5527999977000",
                instagram_url="https://instagram.com/leadfit",
            )
        ]

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)

    batch_response = client.post(
        "/api/prospecting/batches/preview",
        json={
            "niche": "barbearia",
            "city": "Vitoria, ES",
            "limit": 1,
            "enrich": False,
            "validate_phone_format": False,
        },
    )
    assert batch_response.status_code == 200
    batch_payload = batch_response.json()
    assert batch_payload["candidates"][0]["fit_score"] is not None
    assert batch_payload["candidates"][0]["fit_label"] in {"alto", "medio", "baixo"}

    lead_id = _create_lead(client, business_name="Lead KPI", phone_number="+5527999977777")
    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200

    conversations = client.get("/api/conversations").json()["items"]
    target = next(item for item in conversations if item["lead_id"] == lead_id)
    assert target["lead_fit_score"] is not None
    assert target["lead_funnel_stage"] == "contacted"


def test_leads_search_defaults_to_priority_sort(client: TestClient) -> None:
    cold_lead_id = _create_lead(client, business_name="Lead Frio", phone_number="+5527999911101")
    hot_lead_id = _create_lead(client, business_name="Lead Quente", phone_number="+5527999911102")

    client.post(f"/api/leads/{hot_lead_id}/qualify", json={"score": 0.9, "qualification_reason": "Alta intenção"})

    response = client.get("/api/leads/search")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["id"] == hot_lead_id
    assert items[0]["priority_score"] >= items[1]["priority_score"]
    assert items[0]["priority_label"] in {"agora", "alta"}
    assert items[0]["recommended_action"]["label"] in {"Pedir reunião", "Fazer handoff", "Confirmar fit"}


def test_conversations_list_defaults_to_priority_sort(client: TestClient) -> None:
    first_lead_id = _create_lead(client, business_name="Conversa Fria", phone_number="+5527999911201")
    second_lead_id = _create_lead(client, business_name="Conversa Quente", phone_number="+5527999911202")

    first_start = client.post(f"/api/outreach/{first_lead_id}/start")
    second_start = client.post(f"/api/outreach/{second_lead_id}/start")
    assert first_start.status_code == 200
    assert second_start.status_code == 200

    hot_conversation_id = second_start.json()["id"]
    client.post(
        "/webhooks/wasender",
        json={
            "event": "messages.received",
            "data": {
                "messages": {
                    "key": {
                        "id": "priority-inbound-1",
                        "fromMe": False,
                        "remoteJid": "5527999911202@s.whatsapp.net",
                        "cleanedSenderPn": "+5527999911202",
                    },
                    "messageBody": "tenho interesse, podemos agendar uma call",
                    "message": {"conversation": "tenho interesse, podemos agendar uma call"},
                }
            },
        },
        headers={"x-webhook-signature": get_settings().wasender_webhook_secret},
    )

    response = client.get("/api/conversations")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["id"] == hot_conversation_id
    assert items[0]["priority_score"] >= items[1]["priority_score"]
    assert items[0]["priority_label"] in {"agora", "alta"}
    assert items[0]["recommended_action"]["label"] in {"Responder agora", "Pedir reunião", "Revisar agora"}


def test_lead_detail_exposes_recommended_action_for_missing_contact(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Lead Sem Contato", phone_number="+5527999911301")
    client.patch(
        f"/api/leads/{lead_id}",
        json={"phone_number": None, "whatsapp_number": None},
    )

    response = client.get(f"/api/leads/{lead_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_action"]["key"] == "fix_contact"
    assert payload["recommended_action"]["label"] == "Completar contato"


def test_lead_and_conversation_expose_suggested_playbook(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Lead Playbook", phone_number="+5527999911401")
    create_playbook = client.post(
        "/api/playbooks",
        json={
            "name": "Playbook Odonto Contacted",
            "niche": "clinica odontologica",
            "stage": "contacted",
            "instructions": "Conduza a conversa de forma consultiva e leve para diagnóstico rápido.",
            "objection_handling": "Se houver objeção de preço, volte para ROI e previsibilidade.",
            "qualification_rules": "Confirme urgência, autoridade e interesse real.",
            "active": True,
        },
    )
    assert create_playbook.status_code == 200

    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200
    conversation_id = start_response.json()["id"]

    lead_response = client.get(f"/api/leads/{lead_id}")
    assert lead_response.status_code == 200
    lead_payload = lead_response.json()
    assert lead_payload["suggested_playbook"]["name"] == "Playbook Odonto Contacted"

    conversations = client.get("/api/conversations")
    assert conversations.status_code == 200
    thread = next(item for item in conversations.json()["items"] if item["id"] == conversation_id)
    assert thread["suggested_playbook"]["name"] == "Playbook Odonto Contacted"


def test_agent_preview_uses_runtime_offer(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Oficina Orion", phone_number="+5527999944444")
    client.patch(
        "/api/settings/runtime",
        json={"offer_name": "landing page premium", "offer_summary": "pagina para converter mais leads"},
    )

    response = client.post(
        f"/api/leads/{lead_id}/agent-preview",
        json={"custom_instruction": "falar em tom amigavel"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["lead_id"] == lead_id
    assert "landing page premium" in payload["runtime_instruction"]


def test_tasks_listing_and_controls(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Loja Task", phone_number="+5527999955555")
    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200

    tasks_response = client.get("/api/tasks")
    assert tasks_response.status_code == 200
    payload = tasks_response.json()
    assert payload["total"] >= 1
    task_id = payload["items"][0]["id"]

    run_now_response = client.post(f"/api/tasks/{task_id}/run-now")
    assert run_now_response.status_code == 200
    assert run_now_response.json()["status"] == "pending"

    cancel_response = client.post(f"/api/tasks/{task_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


def test_conversation_takeover_and_manual_send(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Loja Humana", phone_number="+5527999966666")
    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200

    conversation_id = client.get("/api/conversations").json()["items"][0]["id"]

    takeover_response = client.post(
        f"/api/conversations/{conversation_id}/takeover",
        json={"operator_name": "gestor"},
    )
    assert takeover_response.status_code == 200
    assert takeover_response.json()["manual_mode"] is True
    assert takeover_response.json()["assignee"] == "gestor"

    settings_response = client.patch(
        f"/api/conversations/{conversation_id}/settings",
        json={"auto_reply_enabled": False, "reply_delay_seconds": 45, "pending_human_review": True},
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["reply_delay_seconds"] == 45

    send_response = client.post(
        f"/api/conversations/{conversation_id}/messages/manual-send",
        json={"operator_name": "gestor", "content": "Mensagem humana real", "mark_as_read": True},
    )
    assert send_response.status_code == 200
    payload = send_response.json()
    assert payload["manual_mode"] is True
    assert payload["messages"][-1]["author_role"] == "human"
    assert payload["messages"][-1]["content"] == "Mensagem humana real"


def test_webhook_from_me_reconciles_existing_outbound_message(monkeypatch, client: TestClient) -> None:
    from app.services import conversation_ops as ops_module

    monkeypatch.setattr(ops_module, "get_settings", lambda: SimpleNamespace(has_wasender_credentials=True))
    monkeypatch.setattr(
        ops_module.WasenderClient,
        "send_text_message",
        lambda self, to, text: {"success": True, "data": {"msgId": 12345, "jid": to, "status": "in_progress"}},
    )
    client.patch("/api/settings/runtime", json={"outbound_enabled": True})

    lead_id = _create_lead(client, business_name="Loja Reconcilia", phone_number="+5527999967777")
    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200
    payload = start_response.json()
    conversation_id = payload["id"]
    original_message = payload["messages"][-1]

    webhook_response = client.post(
        "/webhooks/wasender",
        json={
            "event": "messages.upsert",
            "data": {
                "messages": [
                    {
                        "key": {
                            "id": "3EB0RECONCILE123",
                            "msgId": 12345,
                            "fromMe": True,
                            "remoteJid": "5527999967777@s.whatsapp.net",
                            "cleanedSenderPn": "+5527999967777",
                        },
                        "messageBody": original_message["content"],
                        "message": {"conversation": original_message["content"]},
                    }
                ]
            },
        },
        headers={"x-webhook-signature": get_settings().wasender_webhook_secret},
    )
    assert webhook_response.status_code == 200

    conversation_response = client.get(f"/api/conversations/{conversation_id}")
    assert conversation_response.status_code == 200
    messages = conversation_response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["author_role"] == "agent"
    assert messages[0]["external_message_id"] == "3EB0RECONCILE123"
    assert messages[0]["status"] == "sent"


def test_whatsapp_sessions_manual_create_activate_and_list(client: TestClient) -> None:
    created = client.post(
        "/api/whatsapp-sessions",
        json={
            "name": "Linha nova",
            "phone_number": "+5527999000001",
            "api_key": "session-key-1",
            "webhook_secret": "secret-1",
            "webhook_url": "https://example.com/webhooks/wasender",
            "create_on_provider": False,
            "set_active": True,
        },
    )
    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload["is_active"] is True
    assert created_payload["has_api_key"] is True

    second = client.post(
        "/api/whatsapp-sessions",
        json={
            "name": "Linha antiga",
            "phone_number": "+5527999000002",
            "api_key": "session-key-2",
            "webhook_secret": "secret-2",
            "create_on_provider": False,
            "set_active": False,
        },
    )
    assert second.status_code == 200

    activated = client.post(f"/api/whatsapp-sessions/{second.json()['id']}/activate")
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    workspace = client.get("/api/whatsapp-sessions")
    assert workspace.status_code == 200
    payload = workspace.json()
    assert payload["active_session_id"] == second.json()["id"]
    assert len(payload["items"]) >= 2


def test_conversation_is_separated_by_whatsapp_session(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Loja Multi Linha", phone_number="+5527999011111")

    first_session = client.post(
        "/api/whatsapp-sessions",
        json={
            "name": "Linha A",
            "phone_number": "+5527999000101",
            "api_key": "session-a",
            "webhook_secret": "secret-a",
            "create_on_provider": False,
            "set_active": True,
        },
    ).json()

    first_outreach = client.post(f"/api/outreach/{lead_id}/start")
    assert first_outreach.status_code == 200
    assert first_outreach.json()["whatsapp_session_id"] == first_session["id"]

    second_session = client.post(
        "/api/whatsapp-sessions",
        json={
            "name": "Linha B",
            "phone_number": "+5527999000102",
            "api_key": "session-b",
            "webhook_secret": "secret-b",
            "create_on_provider": False,
            "set_active": True,
        },
    ).json()

    inbound = client.post(
        "/webhooks/wasender",
        json={
            "event": "messages.received",
            "data": {
                "messages": {
                    "key": {
                        "id": "incoming-second-session",
                        "fromMe": False,
                        "remoteJid": "5527999011111@s.whatsapp.net",
                        "cleanedSenderPn": "+5527999011111",
                    },
                    "messageBody": "oi pela segunda linha",
                    "message": {"conversation": "oi pela segunda linha"},
                }
            },
        },
        headers={"x-webhook-signature": "secret-b"},
    )
    assert inbound.status_code == 200

    conversations = client.get("/api/conversations", params={"page": 1, "page_size": 20}).json()["items"]
    same_lead = [item for item in conversations if item["lead_id"] == lead_id]
    assert len(same_lead) == 2
    assert {item["whatsapp_session_id"] for item in same_lead} == {first_session["id"], second_session["id"]}


def test_sync_and_qrcode_routes_use_provider_client(monkeypatch, client: TestClient) -> None:
    from app.services import whatsapp_sessions as session_module

    monkeypatch.setattr(
        session_module.WasenderManagementClient,
        "list_sessions",
        lambda self: [{"id": 77, "name": "Linha Provider", "phone_number": "+5527999000303", "status": "connected"}],
    )
    monkeypatch.setattr(
        session_module.WasenderManagementClient,
        "get_session_details",
        lambda self, session_id: {
            "id": session_id,
            "name": "Linha Provider",
            "phone_number": "+5527999000303",
            "status": "connected",
            "api_key": "provider-api-key",
            "webhook_secret": "provider-secret",
            "webhook_enabled": True,
            "webhook_events": ["messages.received"],
        },
    )
    monkeypatch.setattr(
        session_module.WasenderManagementClient,
        "connect_session",
        lambda self, session_id: {"status": "NEED_SCAN", "qrCode": "provider-qr-connect"},
    )
    monkeypatch.setattr(
        session_module.WasenderManagementClient,
        "get_session_qrcode",
        lambda self, session_id: "provider-qr-refresh",
    )

    synced = client.post("/api/whatsapp-sessions/sync")
    assert synced.status_code == 200
    payload = synced.json()
    assert any(item["name"] == "Linha Provider" for item in payload["items"])

    provider_id = next(item["id"] for item in payload["items"] if item["name"] == "Linha Provider")
    connect = client.post(f"/api/whatsapp-sessions/{provider_id}/connect")
    assert connect.status_code == 200
    assert connect.json()["qr_code"] == "provider-qr-connect"

    refresh = client.get(f"/api/whatsapp-sessions/{provider_id}/qrcode")
    assert refresh.status_code == 200
    assert refresh.json()["qr_code"] == "provider-qr-refresh"


def test_prospecting_batch_review_flow(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Barbearia Flow",
                niche=niche,
                city=city,
                phone_number="+5527999977777",
                instagram_url="https://instagram.com/barbeariaflow",
                source_url="https://instagram.com/barbeariaflow",
                source_query=f'"{niche}" "{city}"',
                source_platform="instagram",
            )
        ]

    def fake_enrich_lead(self, lead) -> dict:
        return {
            "summary": "Precisa de pagina para captar agendamentos.",
            "pain_points": ["depende de DM"],
            "opportunities": ["converter melhor"],
            "evidence": ["instagram forte"],
            "phone_number": "+5527999977777",
        }

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)
    monkeypatch.setattr(management_module.EnrichmentService, "enrich_lead", fake_enrich_lead)

    preview_response = client.post(
        "/api/prospecting/batches/preview",
        json={"niche": "barbearia", "city": "Vitoria, ES", "limit": 1, "enrich": True},
    )
    assert preview_response.status_code == 200
    batch_payload = preview_response.json()
    assert len(batch_payload["candidates"]) == 1
    candidate_id = batch_payload["candidates"][0]["id"]

    apply_response = client.post(
        f"/api/prospecting/batches/{batch_payload['id']}/apply",
        json={"candidate_ids": [candidate_id], "action": "save_only"},
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["candidates"][0]["status"] == "saved"

    search_response = client.get("/api/leads/search", params={"q": "Barbearia Flow"})
    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1


def test_prospecting_batch_preview_without_phone_returns_empty(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Barbearia Sem Numero",
                niche=niche,
                city=city,
                instagram_url="https://instagram.com/barbeariasemnumero",
                source_url="https://instagram.com/barbeariasemnumero",
                source_query=f'"{niche}" "{city}"',
                source_platform="instagram",
            )
        ]

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)

    preview_response = client.post(
        "/api/prospecting/batches/preview",
        json={"niche": "barbearia", "city": "Vitoria, ES", "limit": 1, "enrich": False},
    )
    assert preview_response.status_code == 200
    batch_payload = preview_response.json()
    assert batch_payload["candidates"] == []


def test_prospecting_batch_preview_skips_candidate_without_phone(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Barbearia Sem Numero",
                niche=niche,
                city=city,
                instagram_url="https://instagram.com/barbeariasemnumero",
                source_url="https://instagram.com/barbeariasemnumero",
                source_query=f'"{niche}" "{city}"',
                source_platform="instagram",
            ),
            ProspectLead(
                business_name="Barbearia Com Numero",
                niche=niche,
                city=city,
                phone_number="+5527999977711",
                instagram_url="https://instagram.com/barbeariacomnumero",
                source_url="https://instagram.com/barbeariacomnumero",
                source_query=f'"{niche}" "{city}"',
                source_platform="instagram",
            ),
        ]

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)

    preview_response = client.post(
        "/api/prospecting/batches/preview",
        json={"niche": "barbearia", "city": "Vitoria, ES", "limit": 2, "enrich": False},
    )
    assert preview_response.status_code == 200
    payload = preview_response.json()
    assert len(payload["candidates"]) == 1
    assert payload["candidates"][0]["business_name"] == "Barbearia Com Numero"
    assert payload["candidates"][0]["phone_number"] == "+5527999977711"


def test_campaign_playbook_and_knowledge_feed_agent_instruction(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Clinica Prisma", phone_number="+5527999988888")

    campaign_response = client.post(
        "/api/campaigns",
        json={
            "name": "Campanha Odonto Vix",
            "niche": "clinica odontologica",
            "city": "Vitoria, ES",
            "offer_name": "landing premium",
            "offer_summary": "pagina para gerar consultas",
            "offer_goal": "mais agendamentos",
            "sales_tone": "consultivo",
            "cta_style": "propor conversa curta",
            "is_active": True,
        },
    )
    assert campaign_response.status_code == 200
    assert campaign_response.json()["is_active"] is True

    playbook_response = client.post(
        "/api/playbooks",
        json={
            "name": "Playbook Odonto",
            "niche": "clinica odontologica",
            "stage": "engaged",
            "instructions": "explique que a pagina reduz dependencia de direct",
            "active": True,
        },
    )
    assert playbook_response.status_code == 200

    knowledge_response = client.post(
        "/api/knowledge-items",
        json={
            "title": "Prova social",
            "category": "provas",
            "niche": "clinica odontologica",
            "content": "clinicas convertem melhor quando centralizam campanha e whatsapp",
            "active": True,
        },
    )
    assert knowledge_response.status_code == 200

    preview_response = client.post(f"/api/leads/{lead_id}/agent-preview", json={})
    assert preview_response.status_code == 200
    runtime_instruction = preview_response.json()["runtime_instruction"]
    assert "Campanha Odonto Vix" in runtime_instruction
    assert "Playbook Odonto" in runtime_instruction
    assert "Prova social" in runtime_instruction
    assert "Próxima ação sugerida" in runtime_instruction


def test_agent_preview_contextualizes_instruction_with_suggested_playbook(client: TestClient) -> None:
    lead_id = _create_lead(client, business_name="Clinica Estratégica", phone_number="+5527999988899")

    client.post(
        "/api/playbooks",
        json={
            "name": "Playbook Contacted Estratégico",
            "niche": "clinica odontologica",
            "stage": "contacted",
            "instructions": "Depois do primeiro contato, conduza para diagnóstico rápido com CTA consultivo.",
            "objection_handling": "Se houver resistência, use argumento de previsibilidade comercial.",
            "qualification_rules": "Validar dor, urgência e autoridade.",
            "active": True,
        },
    )

    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200

    preview_response = client.post(f"/api/leads/{lead_id}/agent-preview", json={})
    assert preview_response.status_code == 200
    runtime_instruction = preview_response.json()["runtime_instruction"]
    assert "Próxima ação sugerida" in runtime_instruction
    assert "Playbook sugerido: Playbook Contacted Estratégico" in runtime_instruction
    assert "Depois do primeiro contato, conduza para diagnóstico rápido com CTA consultivo." in runtime_instruction


def test_prospecting_advisor_guides_search(client: TestClient) -> None:
    response = client.post(
        "/api/prospecting/advisor",
        json={
            "message": "quero achar barbearias em vitoria",
            "current_state": {"niche": None, "city": None, "limit": 10, "enrich": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready_to_search"] is True
    assert payload["state"]["niche"] == "barbearia"
    assert payload["state"]["city"] == "Vitoria, ES"


def test_prospecting_advisor_corrects_close_city_typo(client: TestClient) -> None:
    response = client.post(
        "/api/prospecting/advisor",
        json={
            "message": "quero achar barbearias em bitoria es",
            "current_state": {"niche": None, "city": None, "limit": 10, "enrich": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["city"] == "Vitoria, ES"


def test_prospecting_batch_marks_existing_lead_as_duplicate(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module

    _create_lead(client, business_name="Barbearia Flow", phone_number="+5527999977777")

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Barbearia Flow",
                niche=niche,
                city=city,
                phone_number="+5527999977777",
                instagram_url="https://instagram.com/barbeariaflow",
                source_url="https://instagram.com/barbeariaflow",
                source_query=f'"{niche}" "{city}"',
                source_platform="instagram",
            )
        ]

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)

    preview_response = client.post(
        "/api/prospecting/batches/preview",
        json={"niche": "barbearia", "city": "Vitoria, ES", "limit": 1, "enrich": False},
    )
    assert preview_response.status_code == 200
    candidate = preview_response.json()["candidates"][0]
    assert candidate["existing_lead_id"] is not None
    assert candidate["status"] == "duplicate"


def test_manual_send_queues_when_rate_window_is_busy(monkeypatch, client: TestClient) -> None:
    from app.services import conversation_ops as ops_module

    monkeypatch.setattr(ops_module, "get_settings", lambda: SimpleNamespace(has_wasender_credentials=True))
    monkeypatch.setattr(
        ops_module.WasenderClient,
        "send_text_message",
        lambda self, to, text: {"success": True, "data": {"msgId": 12345, "jid": to, "status": "in_progress"}},
    )

    client.patch("/api/settings/runtime", json={"outbound_enabled": True})
    lead_id = _create_lead(client, business_name="Fila Manual", phone_number="+5527999910101")
    start_response = client.post(f"/api/outreach/{lead_id}/start")
    assert start_response.status_code == 200

    conversation_id = client.get("/api/conversations").json()["items"][0]["id"]
    send_response = client.post(
        f"/api/conversations/{conversation_id}/messages/manual-send",
        json={"operator_name": "gestor", "content": "segunda mensagem", "mark_as_read": True},
    )
    assert send_response.status_code == 200
    payload = send_response.json()
    assert payload["messages"][-1]["status"] == "queued_waiting"

    tasks_payload = client.get("/api/tasks").json()["items"]
    assert any(task["task_type"] == "queued_outbound" and task["status"] == "pending" for task in tasks_payload)


def test_batch_save_and_start_marks_queued_contacts(monkeypatch, client: TestClient) -> None:
    from app.api.routes import management as management_module
    from app.services import conversation_ops as ops_module

    monkeypatch.setattr(ops_module, "get_settings", lambda: SimpleNamespace(has_wasender_credentials=True))
    monkeypatch.setattr(
        ops_module.WasenderClient,
        "send_text_message",
        lambda self, to, text: {"success": True, "data": {"msgId": 98765, "jid": to, "status": "in_progress"}},
    )
    client.patch("/api/settings/runtime", json={"outbound_enabled": True})

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Barbearia Fila Um",
                niche=niche,
                city=city,
                phone_number="+5527999910201",
            ),
            ProspectLead(
                business_name="Barbearia Fila Dois",
                niche=niche,
                city=city,
                phone_number="+5527999910202",
            ),
        ]

    monkeypatch.setattr(management_module.ProspectingService, "find_leads", fake_find_leads)

    preview_response = client.post(
        "/api/prospecting/batches/preview",
        json={"niche": "barbearia", "city": "Vitoria, ES", "limit": 2, "enrich": False},
    )
    assert preview_response.status_code == 200
    batch_payload = preview_response.json()

    apply_response = client.post(
        f"/api/prospecting/batches/{batch_payload['id']}/apply",
        json={
            "candidate_ids": [candidate["id"] for candidate in batch_payload["candidates"]],
            "action": "save_and_start_outreach",
        },
    )
    assert apply_response.status_code == 200
    candidates = apply_response.json()["candidates"]
    statuses = {candidate["business_name"]: candidate["status"] for candidate in candidates}
    assert statuses["Barbearia Fila Um"] == "contacted"
    assert statuses["Barbearia Fila Dois"] == "queued_contact"
    first = next(candidate for candidate in candidates if candidate["business_name"] == "Barbearia Fila Um")
    second = next(candidate for candidate in candidates if candidate["business_name"] == "Barbearia Fila Dois")
    assert first["lead_id"] is not None
    assert first["conversation_id"] is not None
    assert first["delivery_status"] == "in_progress"
    assert second["delivery_status"] == "queued_waiting"
