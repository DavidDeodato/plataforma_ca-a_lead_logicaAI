from __future__ import annotations

import difflib
import re
from dataclasses import dataclass


@dataclass
class ProspectingDraft:
    niche: str | None = None
    city: str | None = None
    limit: int = 10
    enrich: bool = True


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
        }

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
