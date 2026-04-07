from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import get_settings


@dataclass
class ProspectingDraft:
    niche: str | None = None
    city: str | None = None
    limit: int = 10
    enrich: bool = True
    recipe_id: int | None = None
    search_goal: str | None = None
    system_prompt: str | None = None
    source_channels: list[str] | None = None
    discovery_mode: str = "hybrid"
    minimum_valid_contacts: int = 10
    require_phone: bool = True
    fallback_enabled: bool = True
    search_depth: int = 2
    agent_max_credits: int | None = None


class ProspectingAdvisorService:
    SUPPORTED_NICHES = {
        "barbearia": ["barbearia", "barbearias", "barber", "barbershop"],
        "clinica odontologica": ["dentista", "dentistas", "odontologia", "odontologico", "clinica odontologica"],
        "escritorio de advocacia": ["advogado", "advogados", "advocacia", "escritorio de advocacia"],
        "salão de beleza": ["salao", "salão", "beleza", "cabeleireiro", "cabeleireira"],
        "academia": ["academia", "academias", "crossfit", "pilates"],
        "oficina mecanica": ["oficina", "oficina mecanica", "mecanica", "auto center"],
        "clinica estetica": ["estetica", "estética", "clinica estetica", "harmonizacao"],
        "imobiliaria": ["imobiliaria", "imóveis", "imoveis", "corretor"],
    }
    CITY_ALIASES = {
        "vitoria": "Vitoria, ES",
        "vitória": "Vitoria, ES",
        "vitoria es": "Vitoria, ES",
        "vitória es": "Vitoria, ES",
        "vitoria espirito santo": "Vitoria, ES",
        "vitória espírito santo": "Vitoria, ES",
        "vila velha": "Vila Velha, ES",
        "serra": "Serra, ES",
        "cariacica": "Cariacica, ES",
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.has_openai_credentials else None

    def advise(self, *, message: str, draft: ProspectingDraft | None = None) -> dict:
        current = draft or ProspectingDraft()
        normalized = self._normalize_text(message)

        niche = current.niche or self._extract_niche(normalized)
        city = self.normalize_city(current.city) if current.city else self._extract_city(normalized)
        limit = self._extract_limit(normalized) or current.limit
        enrich = current.enrich if "sem enriquecer" not in normalized else False

        missing_fields = []
        if not niche:
            missing_fields.append("niche")
        if not city:
            missing_fields.append("city")

        state = {
            "niche": niche,
            "city": city,
            "limit": limit,
            "enrich": enrich,
            "recipe_id": current.recipe_id,
            "search_goal": current.search_goal or f"achar {niche or 'negócios'} em {city or 'uma região definida'}",
            "system_prompt": current.system_prompt or self._default_system_prompt(niche=niche, city=city),
            "source_channels": current.source_channels or ["google", "linkedin", "instagram"],
            "discovery_mode": current.discovery_mode or "hybrid",
            "minimum_valid_contacts": max(limit, current.minimum_valid_contacts or limit),
            "require_phone": current.require_phone,
            "fallback_enabled": current.fallback_enabled,
            "search_depth": current.search_depth or 2,
            "agent_max_credits": current.agent_max_credits,
        }

        llm_overlay = self._llm_overlay(message=message, state=state)
        if llm_overlay:
            state.update({key: value for key, value in llm_overlay.get("state", {}).items() if value is not None})

        if niche and city:
            assistant_message = (
                f"Fechei a busca assim: nicho `{niche}`, cidade `{city}`, limite `{limit}`. "
                "Se quiser, agora e so clicar em gerar lote. Se precisar, eu tambem posso ajustar o nicho ou aumentar o limite."
            )
        elif niche and not city:
            assistant_message = (
                f"Entendi o nicho como `{niche}`. Agora me fala a cidade/estado para eu montar a pesquisa sem chute. "
                "Exemplo: `Vitoria, ES`."
            )
        elif city and not niche:
            assistant_message = (
                f"Entendi a cidade como `{city}`. Agora me fala o tipo de negocio que voce quer encontrar. "
                f"Exemplos que eu reconheco bem: {', '.join(self.supported_niches())}."
            )
        else:
            assistant_message = (
                "Me fala em linguagem natural quem voce quer achar e onde. "
                "Exemplo: `quero achar barbearias em Vitoria, ES`. "
                f"Nichos que eu reconheco melhor: {', '.join(self.supported_niches())}."
            )

        return {
            "assistant_message": assistant_message,
            "state": state,
            "missing_fields": missing_fields,
            "ready_to_search": not missing_fields,
            "supported_niches": self.supported_niches(),
            "supported_cities_hint": sorted(set(self.CITY_ALIASES.values())),
            "recipe_preview": {
                "id": 0,
                "name": llm_overlay.get("recipe_name") if llm_overlay else f"Recipe {niche or 'custom'}",
                "objective": state["search_goal"],
                "system_prompt": state["system_prompt"],
                "source_channels": state["source_channels"],
                "inclusion_rules": llm_overlay.get("inclusion_rules") if llm_overlay else None,
                "exclusion_rules": llm_overlay.get("exclusion_rules") if llm_overlay else None,
                "minimum_valid_contacts": state["minimum_valid_contacts"],
                "max_total_results": max(state["limit"], state["minimum_valid_contacts"]),
                "search_depth": state["search_depth"],
                "require_phone": state["require_phone"],
                "validate_phone_format": True,
                "discovery_mode": state["discovery_mode"],
                "fallback_enabled": state["fallback_enabled"],
                "scoring_guidance": llm_overlay.get("scoring_guidance") if llm_overlay else None,
                "assistant_notes": llm_overlay.get("assistant_notes") if llm_overlay else None,
                "schema_fields": None,
                "agent_max_credits": state["agent_max_credits"],
                "active": True,
                "created_at": "1970-01-01T00:00:00",
                "updated_at": "1970-01-01T00:00:00",
            },
            "warnings": llm_overlay.get("warnings", []) if llm_overlay else [],
            "suggested_variables": llm_overlay.get("suggested_variables", []) if llm_overlay else [],
        }

    def supported_niches(self) -> list[str]:
        return list(self.SUPPORTED_NICHES.keys())

    def _extract_niche(self, normalized_message: str) -> str | None:
        for canonical, aliases in self.SUPPORTED_NICHES.items():
            for alias in aliases:
                if alias in normalized_message:
                    return canonical

        city_match = re.search(r"\bem\s+([a-zA-ZÀ-ÿ\s,]+)", normalized_message)
        candidate = normalized_message
        if city_match:
            candidate = normalized_message[: city_match.start()].strip()

        candidate = re.sub(r"\b(quero|achar|buscar|pesquisar|procurar|clientes|leads|contatos|de|do|da|dos|das)\b", " ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip(" ,.-")
        return candidate or None

    def _extract_city(self, normalized_message: str) -> str | None:
        for alias, canonical in self.CITY_ALIASES.items():
            if alias in normalized_message:
                return canonical

        city_match = re.search(r"\bem\s+([a-zA-ZÀ-ÿ\s,]+)", normalized_message)
        if city_match:
            candidate = city_match.group(1).strip(" .,-")
            return self.normalize_city(candidate)
        return None

    def normalize_city(self, value: str | None) -> str | None:
        if not value:
            return None
        normalized = self._normalize_text(value).replace(",", "")
        for alias, canonical in self.CITY_ALIASES.items():
            if normalized == alias.replace(",", ""):
                return canonical

        alias_keys = list(self.CITY_ALIASES.keys())
        close = difflib.get_close_matches(normalized, alias_keys, n=1, cutoff=0.78)
        if close:
            return self.CITY_ALIASES[close[0]]
        return value.title()

    @staticmethod
    def _extract_limit(normalized_message: str) -> int | None:
        match = re.search(r"\b(\d{1,3})\b", normalized_message)
        if not match:
            return None
        value = int(match.group(1))
        if value < 1:
            return 1
        return min(value, 50)

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.lower().split())

    @staticmethod
    def _default_system_prompt(*, niche: str | None, city: str | None) -> str:
        return (
            f"Procure leads do nicho {niche or 'definir'} em {city or 'definir'}, priorizando sinais fortes de compra, "
            "contato válido e contexto suficiente para outreach personalizado."
        )

    def _llm_overlay(self, *, message: str, state: dict) -> dict:
        if not self.client:
            return {}
        prompt = {
            "user_message": message,
            "current_state": state,
            "goal": "converter linguagem natural em configuração de recipe de prospecção agentica",
        }
        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Voce e um arquiteto de prospecção. Responda apenas JSON com chaves: "
                        '{"recipe_name":"...", "state":{"search_goal":"...", "system_prompt":"...", '
                        '"source_channels":["google"], "discovery_mode":"hybrid", "minimum_valid_contacts":10, '
                        '"require_phone":true, "fallback_enabled":true, "search_depth":2, "agent_max_credits":300}, '
                        '"inclusion_rules":"...", "exclusion_rules":"...", "scoring_guidance":"...", '
                        '"assistant_notes":"...", "warnings":["..."], "suggested_variables":["..."]}'
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
            ],
        )
        output_text = getattr(response, "output_text", "") or ""
        if not output_text:
            return {}
        try:
            data = json.loads(output_text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
