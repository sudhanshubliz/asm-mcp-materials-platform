from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


ELEMENT_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
}
NORMALIZED_ELEMENT_SYMBOLS = {element.lower(): element for element in ELEMENT_SYMBOLS}

COMMON_NAME_ALIASES = {
    "silicon": "Si",
    "gallium arsenide": "GaAs",
    "titanium dioxide": "TiO2",
    "iron oxide": "Fe2O3",
    "lithium iron phosphate": "LiFePO4",
}

MP_ID_PATTERN = re.compile(r"\b(mp-\d+|mp-[A-Za-z0-9-]+)\b", re.IGNORECASE)
FORMULA_TOKEN_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9]{0,14}\b")


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    original_query: str
    tool_name: str
    arguments: dict[str, Any]
    compare_targets: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def _is_formula_candidate(token: str) -> bool:
    parts = re.findall(r"([A-Z][a-z]?)(\d*)", token)
    if not parts:
        return False
    rebuilt = "".join(f"{element}{count}" for element, count in parts)
    return rebuilt == token and all(element in ELEMENT_SYMBOLS for element, _ in parts)


def _extract_formula_candidates(text: str) -> list[str]:
    return [token for token in FORMULA_TOKEN_PATTERN.findall(text) if _is_formula_candidate(token)]


def _extract_alias_formulas(text: str) -> list[str]:
    lowered = text.lower()
    return [formula for alias, formula in COMMON_NAME_ALIASES.items() if alias in lowered]


def _extract_compare_targets(text: str) -> list[str]:
    targets = _extract_alias_formulas(text)
    targets.extend(match.group(1) for match in MP_ID_PATTERN.finditer(text))
    targets.extend(_extract_formula_candidates(text))
    deduped: list[str] = []
    for target in targets:
        normalized = target if target.lower().startswith("mp-") else target
        if normalized not in deduped:
            deduped.append(normalized)
    return deduped[:5]


def _extract_elements(text: str) -> list[str]:
    lowered = text.lower()
    for marker in ("containing", "contains", "with elements", "including", "include"):
        if marker not in lowered:
            continue
        fragment = text[lowered.index(marker) + len(marker) :]
        fragment = re.split(r"\b(with|where|between|compare|band gap|density)\b", fragment, maxsplit=1)[0]
        tokens = re.findall(r"\b([A-Za-z][a-z]?)\b", fragment)
        elements = [NORMALIZED_ELEMENT_SYMBOLS[token.lower()] for token in tokens if token.lower() in NORMALIZED_ELEMENT_SYMBOLS]
        if elements:
            return list(dict.fromkeys(elements))
    return []


def _extract_range_arguments(text: str) -> dict[str, Any]:
    lowered = text.lower()
    arguments: dict[str, Any] = {}
    patterns = {
        "band_gap": r"band gap(?: between| from)?\s*([0-9]*\.?[0-9]+)?(?:\s*(?:and|to|-)\s*([0-9]*\.?[0-9]+))?",
        "density": r"density(?: between| from)?\s*([0-9]*\.?[0-9]+)?(?:\s*(?:and|to|-)\s*([0-9]*\.?[0-9]+))?",
    }
    for field_name, pattern in patterns.items():
        match = re.search(pattern, lowered)
        if not match:
            continue
        minimum = float(match.group(1)) if match.group(1) else None
        maximum = float(match.group(2)) if match.group(2) else None
        if minimum is not None:
            arguments[f"{field_name}_min"] = minimum
        if maximum is not None:
            arguments[f"{field_name}_max"] = maximum
    return arguments


def parse_user_query(query: str) -> QueryPlan:
    normalized_query = _normalize_whitespace(query)
    lowered = normalized_query.lower()

    compare_targets = _extract_compare_targets(normalized_query)
    if (
        "compare" in lowered
        or "comparison" in lowered
        or "vs" in lowered
    ) and 2 <= len(compare_targets) <= 5:
        return QueryPlan(
            intent="compare",
            original_query=normalized_query,
            tool_name="compare",
            arguments={},
            compare_targets=compare_targets,
            notes=["Resolved comparison targets from formulas, mp-ids, and common material names."],
        )

    material_ids = [match.group(1) for match in MP_ID_PATTERN.finditer(normalized_query)]
    if len(material_ids) == 1:
        return QueryPlan(
            intent="material_id_lookup",
            original_query=normalized_query,
            tool_name="get_material_by_id_tool",
            arguments={"material_id": material_ids[0]},
        )

    alias_formulas = _extract_alias_formulas(normalized_query)
    formulas = _extract_formula_candidates(normalized_query)
    if alias_formulas:
        formulas = [*alias_formulas, *[formula for formula in formulas if formula not in alias_formulas]]

    elements = _extract_elements(normalized_query)
    range_arguments = _extract_range_arguments(normalized_query)
    structured_search = bool(elements or range_arguments)

    if formulas and not structured_search and len(formulas) == 1:
        return QueryPlan(
            intent="formula_lookup",
            original_query=normalized_query,
            tool_name="search_material_tool",
            arguments={"formula": formulas[0], "limit": 10, "offset": 0},
        )

    if structured_search:
        arguments: dict[str, Any] = {"query": normalized_query, "limit": 20, "offset": 0}
        if elements:
            arguments["elements"] = elements
        arguments.update(range_arguments)
        return QueryPlan(
            intent="advanced_search",
            original_query=normalized_query,
            tool_name="search_materials_advanced_tool",
            arguments=arguments,
        )

    return QueryPlan(
        intent="chat_search",
        original_query=normalized_query,
        tool_name="ask_materials_project_tool",
        arguments={"question": normalized_query, "limit": 20, "offset": 0},
    )
