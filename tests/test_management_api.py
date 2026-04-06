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


def test_dashboard_summary(client: TestClient) -> None:
    _create_lead(client)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["leads"] >= 1
    assert payload["safe_mode"]["outbound_enabled"] is False


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
    assert qualified_payload["qualified_lead"]["score"] == 0.9

    disqualify_response = client.post(f"/api/leads/{lead_id}/disqualify")
    assert disqualify_response.status_code == 200
    assert disqualify_response.json()["status"] == "do_not_contact"


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
