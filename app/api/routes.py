from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.models.schemas import (
    CanonicalRecipe,
    ContinueRequest,
    GenerateRequest,
    GenerateResponse,
    RecipeResponse,
)
from app.services.generator import RecipeGenerator
from app.services.translation import TranslationService
from app.storage.recipes import RecipeRepo
from app.storage.robot_profiles import RobotProfileRepo
from app.storage.cache import Cache
from app.xai.client import XAIClient

# Hardcoded tooling model (do not override via env)
MODEL_TOOLING_HARDCODED = "grok-4-1-fast-non-reasoning"


router = APIRouter(prefix="/v1", tags=["v1"])

# MVP state (in-memory)
cache = Cache(ttl_s=settings.CACHE_TTL_S, maxsize=settings.CACHE_MAXSIZE)

# In-memory sessions (MVP). For prod: Redis/Postgres.
# session_id -> state
sessions: dict[str, dict[str, Any]] = {}

recipe_repo = RecipeRepo(settings.RECIPES_DIR)
robot_repo = RobotProfileRepo(settings.ROBOT_PROFILES_DIR)

xai = XAIClient(settings.XAI_BASE_URL, settings.XAI_API_KEY, timeout_s=settings.XAI_TIMEOUT_S)
translator = TranslationService(xai=xai, model=settings.XAI_MODEL_GENERAL, store=settings.XAI_STORE_MESSAGES)

generator = RecipeGenerator(
    xai=xai,
    model_tooling=MODEL_TOOLING_HARDCODED,
    model_general=settings.XAI_MODEL_GENERAL,
    translator=translator,
    store=settings.XAI_STORE_MESSAGES,
    allowed_domains=[d.strip() for d in settings.WEB_ALLOWED_DOMAINS.split(",") if d.strip()] or None,
    excluded_domains=[d.strip() for d in settings.WEB_EXCLUDED_DOMAINS.split(",") if d.strip()] or None,
)

# Mapping rules (MVP; move to DB/config later)
MAPPING_RULES = {
    "verbs_to_modes": {
        "измельч": "CHOP",
        "нареж": "CHOP",
        "смеш": "MIX",
        "взбей": "WHISK",
        "замес": "KNEAD",
        "нагре": "HEAT",
        "вари": "HEAT",
        "туш": "HEAT",
        "пари": "STEAM",
    }
}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME}


@router.get("/recipes")
async def list_recipes(lang: str = Query(default="ru")) -> dict[str, Any]:
    # MVP: list meta only; localization for titles can be added later.
    return {"items": recipe_repo.list_meta(), "lang": lang}


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: str, lang: str = Query(default="ru")) -> RecipeResponse:
    recipe = recipe_repo.get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="recipe_not_found")

    localized = await translator.localize(recipe, lang)
    return RecipeResponse(
        recipe_id=recipe_id,
        lang=lang,
        origin="internal",
        canonical_recipe=recipe,
        localized=localized,
        robot_program=[],
        manual_steps=[],
        warnings=[],
        questions=[],
        source_urls=[],
    )


@router.post("/recipes/generate", response_model=GenerateResponse)
async def generate_recipe(req: GenerateRequest) -> GenerateResponse:
    """
    Initial call:
      - extracts canonical recipe via web_search tool
      - adapts to robot profile
      - if questions remain -> returns session_id + questions[]
      - else returns session_id + full result
    """
    if not settings.XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY_not_configured")

    profile = robot_repo.get(req.robot_model)
    if not profile:
        raise HTTPException(status_code=404, detail="robot_profile_not_found")

    session_id, result, questions, canonical, plan = await generator.generate_from_web(req, profile, MAPPING_RULES)

    # Store session state for /continue
    sessions[session_id] = {
        "req": req.model_dump(),
        "robot_model": req.robot_model,
        "canonical_recipe": canonical.model_dump(),
        "answers": {},  # accumulated
        "last_questions": questions,
    }

    return GenerateResponse(session_id=session_id, result=result, questions=questions)


@router.post("/recipes/generate/continue", response_model=GenerateResponse)
async def generate_continue(req: ContinueRequest) -> GenerateResponse:
    """
    Continue call:
      - merges answers into session
      - reruns adapt+validate (+localize) using stored canonical recipe
      - returns questions[] if still missing data, or full result if resolved
    """
    state = sessions.get(req.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session_not_found")

    if not settings.XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY_not_configured")

    stored_req = GenerateRequest.model_validate(state["req"])
    profile = robot_repo.get(stored_req.robot_model)
    if not profile:
        raise HTTPException(status_code=404, detail="robot_profile_not_found")

    # Merge answers (accumulate)
    merged_answers: dict[str, Any] = dict(state.get("answers", {}))
    merged_answers.update(req.answers or {})
    state["answers"] = merged_answers

    canonical = CanonicalRecipe.model_validate(state["canonical_recipe"])

    result, questions, plan = await generator.resume_adaptation(
        session_id=req.session_id,
        canonical=canonical,
        profile=profile,
        mapping_rules=MAPPING_RULES,
        req=stored_req,
        answers=merged_answers,
    )

    state["last_questions"] = questions

    return GenerateResponse(session_id=req.session_id, result=result, questions=questions)
