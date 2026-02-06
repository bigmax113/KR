from __future__ import annotations


def prompt_extract_recipe(query: str) -> tuple[str, str]:
    system = (
        "You are a culinary data extraction engine. "
        "Your job: find a recipe by name using web search if needed, then extract it into the given JSON schema. "
        "Do NOT invent ingredients or steps. Prefer authoritative sources. "
        "Keep quantities and units consistent; if missing, set them to null. "
        "Return ONLY valid JSON conforming to the schema."
    )
    user = (
        f"Recipe name: {query}\n"
        "Use web search to find 2-3 sources. Extract one coherent recipe variant.\n"
        "Include source URLs in source_urls.\n"
        "Output must be JSON only."
    )
    return system, user


def prompt_adapt_to_robot() -> tuple[str, str]:
    system = (
        "You are a cooking-to-robot planner. "
        "Given a canonical recipe, a robot profile, mapping hints, constraints, and prior answers, "
        "output a robot plan in the schema. "
        "Never exceed robot limits. If impossible, add cannot_map and ask questions."
    )
    user = (
        "Create a robot_program compatible with the robot profile.\n"
        "Also provide manual_steps (what user does), warnings, questions if needed.\n"
        "If 'answers' are provided, use them to resolve earlier questions and avoid re-asking.\n"
        "Return ONLY valid JSON for the RobotPlan schema."
    )
    return system, user


def prompt_localize(lang: str) -> tuple[str, str]:
    system = (
        "You are a professional culinary translator. "
        "Translate recipe title, ingredients list and steps into the target language. "
        "Do not change quantities, units, or meaning."
    )
    user = (
        f"Target language: {lang}\n"
        "Return ONLY JSON for the LocalizedRecipe schema."
    )
    return system, user
