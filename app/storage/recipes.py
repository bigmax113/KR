from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.models.schemas import CanonicalRecipe


class RecipeRepo:
    def __init__(self, recipes_dir: str):
        self.recipes_dir = Path(recipes_dir)

    def list_meta(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for p in sorted(self.recipes_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                out.append({
                    "id": p.stem,
                    "title": data.get("title", ""),
                    "tags": data.get("tags", []),
                    "prep_min": data.get("prep_min"),
                    "cook_min": data.get("cook_min"),
                })
            except Exception:
                continue
        return out

    def get(self, recipe_id: str) -> Optional[CanonicalRecipe]:
        p = self.recipes_dir / f"{recipe_id}.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return CanonicalRecipe.model_validate(data)

    def save(self, recipe_id: str, recipe: CanonicalRecipe) -> None:
        p = self.recipes_dir / f"{recipe_id}.json"
        p.write_text(recipe.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
