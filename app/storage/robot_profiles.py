from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.models.schemas import RobotProfile


class RobotProfileRepo:
    def __init__(self, profiles_dir: str):
        self.profiles_dir = Path(profiles_dir)

    def get(self, robot_model: str) -> Optional[RobotProfile]:
        p = self.profiles_dir / f"{robot_model}.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return RobotProfile.model_validate(data)
