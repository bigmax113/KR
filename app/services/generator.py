from __future__ import annotations

import uuid
from typing import Any, Optional

from app.models.schemas import (
    CanonicalRecipe,
    GenerateRequest,
    LocalizedRecipe,
    Origin,
    RecipeResponse,
    RobotPlan,
    RobotProfile,
)
from app.services.prompts import prompt_adapt_to_robot, prompt_extract_recipe
from app.services.translation import TranslationService, pydantic_to_response_format
from app.validators.robot_validator import RobotPlanValidator
from app.xai.client import XAIClient


def web_search_tool(allowed_domains: list[str] | None, excluded_domains: list[str] | None) -> dict[str, Any]:
    """
    Web search tool descriptor.

    Notes:
      - Prefer server-side execution only.
      - Keep domain allow/deny lists small.
    """
    tool: dict[str, Any] = {"type": "web_search"}
    if allowed_domains:
        tool["allowed_domains"] = allowed_domains[:5]
    if excluded_domains:
        tool["excluded_domains"] = excluded_domains[:5]
    return tool


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


class RecipeGenerator:
    def __init__(
        self,
        *,
        xai: XAIClient,
        model_tooling: str,
        model_general: str,
        translator: TranslationService,
        store: bool = False,
        allowed_domains: Optional[list[str]] = None,
        excluded_domains: Optional[list[str]] = None,
    ):
        self.xai = xai
        self.model_tooling = model_tooling
        self.model_general = model_general
        self.translator = translator
        self.store = store
        self.allowed_domains = allowed_domains or []
        self.excluded_domains = excluded_domains or []

    async def generate_from_web(
        self,
        req: GenerateRequest,
        profile: RobotProfile,
        mapping_rules: dict[str, Any],
    ) -> tuple[str, Optional[RecipeResponse], list[dict[str, Any]], CanonicalRecipe, RobotPlan]:
        """
        Full pipeline (initial):
          web_search + extract -> adapt -> validate -> localize -> assemble

        Returns:
          session_id, result_or_none, questions, canonical_recipe, robot_plan
        """
        session_id = str(uuid.uuid4())

        # 1) Search+Extract (tooling model, structured output)
        sys, usr = prompt_extract_recipe(req.query)
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": usr},
        ]
        tools = [web_search_tool(self.allowed_domains or None, self.excluded_domains or None)]
        resp = await self.xai.create_response(
            model=self.model_tooling,
            input_messages=messages,
            tools=tools,
            response_format=pydantic_to_response_format(CanonicalRecipe),
            store=self.store,
            max_output_tokens=3000,
        )
        recipe_json = self.xai.extract_output_text(resp)
        canonical = CanonicalRecipe.model_validate_json(recipe_json)

        # 2) Adapt to robot (general model, structured output)
        plan = await self.adapt_only(
            canonical=canonical,
            profile=profile,
            mapping_rules=mapping_rules,
            req=req,
            answers={},  # no answers yet
        )

        # 3) Validate locally (clamp + warnings)
        plan = RobotPlanValidator.validate(plan, profile)

        # 4) Localize (for UI; can be delayed until questions resolved if you want)
        localized = await self.translator.localize(canonical, req.lang)

        result = self._assemble(
            recipe_id=session_id,
            origin=Origin.web,
            canonical=canonical,
            localized=localized,
            plan=plan,
            lang=req.lang,
        )

        if plan.questions:
            return session_id, None, plan.questions, canonical, plan

        return session_id, result, [], canonical, plan

    async def resume_adaptation(
        self,
        *,
        session_id: str,
        canonical: CanonicalRecipe,
        profile: RobotProfile,
        mapping_rules: dict[str, Any],
        req: GenerateRequest,
        answers: dict[str, Any],
    ) -> tuple[Optional[RecipeResponse], list[dict[str, Any]], RobotPlan]:
        """
        Resume from stored canonical recipe + user answers:
          adapt -> validate -> localize -> assemble
        """
        plan = await self.adapt_only(
            canonical=canonical,
            profile=profile,
            mapping_rules=mapping_rules,
            req=req,
            answers=answers or {},
        )
        plan = RobotPlanValidator.validate(plan, profile)

        localized = await self.translator.localize(canonical, req.lang)
        result = self._assemble(
            recipe_id=session_id,
            origin=Origin.web,
            canonical=canonical,
            localized=localized,
            plan=plan,
            lang=req.lang,
        )

        if plan.questions:
            return None, plan.questions, plan

        return result, [], plan

    async def adapt_only(
        self,
        *,
        canonical: CanonicalRecipe,
        profile: RobotProfile,
        mapping_rules: dict[str, Any],
        req: GenerateRequest,
        answers: dict[str, Any],
    ) -> RobotPlan:
        """
        Adaptation step only (LLM planner).

        Inputs:
          - canonical recipe
          - robot profile and limits
          - mapping rules
          - request constraints
          - user answers (from previous questions)

        Output:
          - RobotPlan JSON (robot_program/manual_steps/warnings/questions/cannot_map)
        """
        sys, usr = prompt_adapt_to_robot()
        payload = {
            "recipe": canonical.model_dump(),
            "robot_profile": profile.model_dump(),
            "mapping_rules": mapping_rules,
            "constraints": req.constraints,
            "answers": answers,
            "target_language": req.lang,
            "recipe_query": req.query,
        }
        messages = [
            {"role": "system", "content": sys},
            {
                "role": "user",
                "content": (
                    usr
                    + "\n\nIMPORTANT:\n"
                    + "- Use 'answers' to resolve previous questions.\n"
                    + "- If still missing data, return questions[] with concise prompts.\n"
                    + "- Never exceed robot limits.\n"
                    + "- robot_program should be runnable and explicit (mode/speed/temp/duration/attachment).\n"
                    + "\n\nINPUT_PAYLOAD:\n"
                    + json_dumps(payload)
                ),
            },
        ]
        resp = await self.xai.create_response(
            model=self.model_general,
            input_messages=messages,
            response_format=pydantic_to_response_format(RobotPlan),
            store=self.store,
            max_output_tokens=2500,
        )
        txt = self.xai.extract_output_text(resp)
        return RobotPlan.model_validate_json(txt)

    def _assemble(
        self,
        *,
        recipe_id: str,
        origin: Origin,
        canonical: CanonicalRecipe,
        localized: LocalizedRecipe,
        plan: RobotPlan,
        lang: str,
    ) -> RecipeResponse:
        return RecipeResponse(
            recipe_id=recipe_id,
            lang=lang,
            origin=origin,
            canonical_recipe=canonical,
            localized=localized,
            robot_program=plan.robot_program,
            manual_steps=plan.manual_steps,
            warnings=plan.warnings,
            questions=plan.questions,
            source_urls=canonical.source_urls,
        )
