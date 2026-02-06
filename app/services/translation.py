from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel

from app.models.schemas import CanonicalRecipe, LocalizedRecipe
from app.services.prompts import prompt_localize
from app.xai.client import XAIClient


def pydantic_to_response_format(schema_model: type[BaseModel]) -> dict:
    # OpenAI-style json_schema response_format
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_model.__name__,
            "schema": schema_model.model_json_schema(),
            "strict": True,
        },
    }


class TranslationService:
    def __init__(self, xai: XAIClient, model: str, store: bool = False):
        self.xai = xai
        self.model = model
        self.store = store

    async def localize(self, recipe: CanonicalRecipe, lang: str) -> LocalizedRecipe:
        if lang.lower().startswith("ru"):
            return LocalizedRecipe(
                title=recipe.title,
                ingredients=[self._fmt_ing(i) for i in recipe.ingredients],
                steps=[s.text for s in recipe.steps],
            )

        sys, usr = prompt_localize(lang)
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": usr + "\n\n" + recipe.model_dump_json(ensure_ascii=False)},
        ]
        resp = await self.xai.create_response(
            model=self.model,
            input_messages=messages,
            response_format=pydantic_to_response_format(LocalizedRecipe),
            store=self.store,
        )
        text = self.xai.extract_output_text(resp)
        return LocalizedRecipe.model_validate_json(text)

    @staticmethod
    def _fmt_ing(i) -> str:
        if i.qty is None or i.unit is None:
            return i.name
        return f"{i.name} — {i.qty:g} {i.unit.value}"
