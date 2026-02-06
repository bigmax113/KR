from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Origin(str, Enum):
    internal = "internal"
    web = "web"


class QuantityUnit(str, Enum):
    g = "g"
    kg = "kg"
    ml = "ml"
    l = "l"
    pcs = "pcs"
    tsp = "tsp"
    tbsp = "tbsp"


class Ingredient(BaseModel):
    name: str = Field(description="Ingredient name in canonical language (RU in MVP).")
    qty: Optional[float] = Field(default=None, description="Quantity (normalized where possible).")
    unit: Optional[QuantityUnit] = Field(default=None, description="Unit for qty.")
    notes: Optional[str] = None


class Step(BaseModel):
    idx: int = Field(ge=1)
    text: str = Field(description="Human-readable step text (canonical/RU).")
    # Optional structured hints for adaptation
    action_type: Optional[Literal["CHOP","MIX","WHISK","KNEAD","HEAT","STEAM","REST","BAKE","FRY","BOIL","UNKNOWN"]] = "UNKNOWN"
    duration_sec: Optional[int] = Field(default=None, ge=0)
    temperature_c: Optional[int] = Field(default=None, ge=0)
    speed: Optional[int] = Field(default=None, ge=0)
    attachment: Optional[str] = None


class CanonicalRecipe(BaseModel):
    title: str
    servings: Optional[int] = Field(default=None, ge=1)
    prep_min: Optional[int] = Field(default=None, ge=0)
    cook_min: Optional[int] = Field(default=None, ge=0)
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class RobotModeSpec(BaseModel):
    mode: str
    speed_range: Optional[tuple[int,int]] = None
    temp_c_range: Optional[tuple[int,int]] = None
    max_duration_sec: Optional[int] = None
    supports_pulse: Optional[bool] = None
    stir_speeds: Optional[list[int]] = None


class RobotProfile(BaseModel):
    robot_model: str
    bowl_capacity_ml: int = Field(ge=100)
    bowl_max_fill_ml: int = Field(ge=100)
    bowl_max_mass_g: int = Field(ge=50)
    attachments: list[str] = Field(default_factory=list)
    modes: list[RobotModeSpec] = Field(default_factory=list)
    idioms: dict[str, Any] = Field(default_factory=dict)


class RobotProgramStep(BaseModel):
    mode: str
    duration_sec: int = Field(ge=0)
    speed: Optional[int] = Field(default=None, ge=0)
    temperature_c: Optional[int] = Field(default=None, ge=0)
    attachment: Optional[str] = None
    notes: Optional[str] = None


class RobotPlan(BaseModel):
    robot_program: list[RobotProgramStep] = Field(default_factory=list)
    manual_steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    questions: list[dict[str, Any]] = Field(default_factory=list)
    cannot_map: list[str] = Field(default_factory=list)


class LocalizedRecipe(BaseModel):
    title: str
    ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class RecipeResponse(BaseModel):
    recipe_id: str
    lang: str
    origin: Origin
    canonical_recipe: CanonicalRecipe
    localized: LocalizedRecipe
    robot_program: list[RobotProgramStep] = Field(default_factory=list)
    manual_steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    questions: list[dict[str, Any]] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    lang: str = Field(default="ru", min_length=2, max_length=10)
    robot_model: str = Field(min_length=1, max_length=80)
    constraints: dict[str, Any] = Field(default_factory=dict)


class ContinueRequest(BaseModel):
    session_id: str
    answers: dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    session_id: str
    result: Optional[RecipeResponse] = None
    questions: list[dict[str, Any]] = Field(default_factory=list)
