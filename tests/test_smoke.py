from __future__ import annotations

import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_smoke.db"
os.environ["OUTBOUND_ENABLED"] = "false"
os.environ["AUTO_REPLY_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["WASENDER_API_KEY"] = ""
os.environ["WASENDER_WEBHOOK_SECRET"] = ""

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, engine
from app.services.prospecting import ProspectLead, ProspectingService


@pytest.fixture
def client() -> TestClient:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_readiness_safe_mode(client: TestClient) -> None:
    response = client.get("/api/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["safe_mode"]["outbound_enabled"] is False
    assert payload["safe_mode"]["auto_reply_enabled"] is False


def test_create_lead(client: TestClient) -> None:
    response = client.post(
        "/api/leads",
        json={
            "business_name": "Barbearia Exemplo",
            "niche": "barbearia",
            "city": "Vitoria, ES",
            "phone_number": "+5527999999999",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["business_name"] == "Barbearia Exemplo"


def test_prospecting_run_with_stubs(monkeypatch, client: TestClient) -> None:
    from app.api.routes import leads as leads_module

    def fake_find_leads(self, niche: str, city: str, limit: int = 10) -> list[ProspectLead]:
        return [
            ProspectLead(
                business_name="Studio Sorriso",
                niche=niche,
                city=city,
                phone_number="+5527988800001",
                instagram_url="https://instagram.com/studiosorriso",
                source_url="https://instagram.com/studiosorriso",
                source_query=f'"{niche}" "{city}"',
                source_platform="instagram",
            )
        ]

    def fake_enrich_lead(self, lead) -> dict:
        return {
            "summary": "Clinica local com presenca basica em rede social.",
            "pain_points": ["Nao tem pagina de vendas dedicada"],
            "opportunities": ["Captar mais agendamentos"],
            "evidence": ["Perfil no Instagram"],
            "website": None,
            "instagram_url": "https://instagram.com/studiosorriso",
            "phone_number": "+5527988800001",
        }

    monkeypatch.setattr(leads_module.ProspectingService, "find_leads", fake_find_leads)
    monkeypatch.setattr(leads_module.EnrichmentService, "enrich_lead", fake_enrich_lead)

    response = client.post(
        "/api/prospecting/run",
        json={"niche": "clinica odontologica", "city": "Vitoria, ES", "limit": 1, "enrich": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["business_name"] == "Studio Sorriso"


def test_prospecting_service_ignores_results_without_phone(monkeypatch) -> None:
    service = ProspectingService()

    def fake_search(self, query: str, limit: int = 5, location: str | None = None) -> list[dict]:
        if "whatsapp" in query:
            return [
                {
                    "url": "https://instagram.com/semnumero",
                    "title": "Barbearia Sem Numero",
                    "description": "Perfil sem contato visivel",
                    "markdown": "Atendimento premium sem telefone no perfil.",
                },
                {
                    "url": "https://instagram.com/comnumero1",
                    "title": "Barbearia Numero Um",
                    "description": "Whatsapp +55 27 99999-0001",
                    "markdown": "Contato rapido no +55 27 99999-0001",
                },
            ]
        if "telefone" in query:
            return [
                {
                    "url": "https://instagram.com/comnumero2",
                    "title": "Barbearia Numero Dois",
                    "description": "Telefone +55 27 99999-0002",
                    "markdown": "Agendamentos pelo numero +55 27 99999-0002",
                }
            ]
        return []

    monkeypatch.setattr("app.services.prospecting.FirecrawlClient.search", fake_search)

    leads = service.find_leads(niche="barbearia", city="Vitoria, ES", limit=2)

    assert len(leads) == 2
    assert all(lead.phone_number for lead in leads)
    assert {lead.business_name for lead in leads} == {"Barbearia Numero Um", "Barbearia Numero Dois"}


def test_prospecting_service_optional_phone_validation(monkeypatch) -> None:
    def fake_search(self, query: str, limit: int = 5, location: str | None = None) -> list[dict]:
        return [
            {
                "url": "https://instagram.com/numeroinvalido",
                "title": "Barbearia Numero Invalido",
                "description": "Contato 051 99381-14779",
                "markdown": "Telefone 051 99381-14779",
            },
            {
                "url": "https://instagram.com/numerovalido",
                "title": "Barbearia Numero Valido",
                "description": "Contato +55 27 99999-1234",
                "markdown": "Telefone +55 27 99999-1234",
            },
        ]

    monkeypatch.setattr("app.services.prospecting.FirecrawlClient.search", fake_search)

    loose_service = ProspectingService(validate_phone_format=False)
    strict_service = ProspectingService(validate_phone_format=True)

    loose = loose_service.find_leads(niche="barbearia", city="Vitoria, ES", limit=2)
    strict = strict_service.find_leads(niche="barbearia", city="Vitoria, ES", limit=2)

    assert any(lead.business_name == "Barbearia Numero Invalido" for lead in loose)
    assert all(lead.business_name != "Barbearia Numero Invalido" for lead in strict)
    assert any(lead.business_name == "Barbearia Numero Valido" for lead in strict)


def test_outreach_starts_in_draft_mode(client: TestClient) -> None:
    response = client.post(
        "/api/leads",
        json={
            "business_name": "Loja Draft",
            "niche": "barbearia",
            "city": "Vitoria, ES",
            "phone_number": "+5527988800002",
        },
    )
    lead_id = response.json()["id"]

    outreach_response = client.post(f"/api/outreach/{lead_id}/start")
    assert outreach_response.status_code == 200
    payload = outreach_response.json()
    assert payload["stage"] == "contacted"

    conversation_response = client.get(f"/api/leads/{lead_id}/conversation")
    messages = conversation_response.json()["messages"]
    assert len(messages) >= 1
    assert messages[-1]["status"] == "draft_only"


def test_webhook_inbound_persists_message_without_auto_reply(client: TestClient) -> None:
    payload = {
        "event": "messages.upsert",
        "timestamp": 1633456789,
        "data": {
            "messages": [
                {
                    "key": {
                        "id": "incoming-1",
                        "fromMe": False,
                        "remoteJid": "5527988800003@s.whatsapp.net",
                        "cleanedSenderPn": "+5527988800003",
                    },
                    "messageBody": "Tenho interesse, pode explicar melhor?",
                    "message": {"conversation": "Tenho interesse, pode explicar melhor?"},
                }
            ]
        },
    }

    response = client.post("/webhooks/wasender", json=payload)
    assert response.status_code == 200

    leads_response = client.get("/api/leads")
    leads = leads_response.json()
    created = next(item for item in leads if item["phone_number"] == "+5527988800003")

    conversation_response = client.get(f"/api/leads/{created['id']}/conversation")
    messages = conversation_response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["direction"] == "inbound"


def test_webhook_messages_received_persists_message_without_auto_reply(client: TestClient) -> None:
    payload = {
        "event": "messages.received",
        "timestamp": 1633456790,
        "data": {
            "messages": {
                "key": {
                    "id": "incoming-received-1",
                    "fromMe": False,
                    "remoteJid": "5527988800004@s.whatsapp.net",
                    "cleanedSenderPn": "+5527988800004",
                },
                "messageBody": "teste-recebido",
                "message": {"conversation": "teste-recebido"},
            }
        },
    }

    response = client.post("/webhooks/wasender", json=payload)
    assert response.status_code == 200

    leads_response = client.get("/api/leads")
    leads = leads_response.json()
    created = next(item for item in leads if item["phone_number"] == "+5527988800004")

    conversation_response = client.get(f"/api/leads/{created['id']}/conversation")
    messages = conversation_response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["direction"] == "inbound"
    assert messages[0]["content"] == "teste-recebido"
