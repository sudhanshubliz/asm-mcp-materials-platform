from streamlit_ui.services.query_parser import parse_user_query


def test_parse_query_detects_material_id_lookup():
    plan = parse_user_query("Get properties for mp-149")

    assert plan.intent == "material_id_lookup"
    assert plan.tool_name == "get_material_by_id_tool"
    assert plan.arguments["material_id"] == "mp-149"


def test_parse_query_detects_compare_from_common_names():
    plan = parse_user_query("Compare silicon and gallium arsenide")

    assert plan.intent == "compare"
    assert plan.compare_targets == ["Si", "GaAs"]


def test_parse_query_detects_structured_advanced_search():
    plan = parse_user_query("Show materials containing Si and O with band gap between 0.5 and 1.0 eV")

    assert plan.intent == "advanced_search"
    assert plan.tool_name == "search_materials_advanced_tool"
    assert plan.arguments["elements"] == ["Si", "O"]
    assert plan.arguments["band_gap_min"] == 0.5
    assert plan.arguments["band_gap_max"] == 1.0


def test_parse_query_normalizes_lowercase_elements():
    plan = parse_user_query("show materials containing si and o with band gap between 0.5 and 1.0 eV")

    assert plan.intent == "advanced_search"
    assert plan.arguments["elements"] == ["Si", "O"]


def test_parse_query_routes_battery_cathode_prompt_to_chat_search():
    plan = parse_user_query("Find stable cathode materials for batteries")

    assert plan.intent == "chat_search"
    assert plan.tool_name == "ask_materials_project_tool"
    assert plan.arguments["question"] == "Find stable cathode materials for batteries"
