from __future__ import annotations

from app.models.schemas import RobotPlan, RobotProfile


class RobotPlanValidator:
    @staticmethod
    def validate(plan: RobotPlan, profile: RobotProfile) -> RobotPlan:
        # Hard validation: clamp values into allowed ranges and add warnings.
        mode_index = {m.mode: m for m in profile.modes}
        for s in plan.robot_program:
            spec = mode_index.get(s.mode)
            if not spec:
                plan.warnings.append(f"Mode '{s.mode}' is not in robot profile.")
                continue

            if spec.max_duration_sec is not None and s.duration_sec > spec.max_duration_sec:
                plan.warnings.append(f"{s.mode}: duration {s.duration_sec}s > max {spec.max_duration_sec}s; clamped.")
                s.duration_sec = spec.max_duration_sec

            if s.speed is not None and spec.speed_range is not None:
                lo, hi = spec.speed_range
                if s.speed < lo or s.speed > hi:
                    plan.warnings.append(f"{s.mode}: speed {s.speed} out of range {lo}-{hi}; clamped.")
                    s.speed = min(max(s.speed, lo), hi)

            if s.temperature_c is not None and spec.temp_c_range is not None:
                lo, hi = spec.temp_c_range
                if s.temperature_c < lo or s.temperature_c > hi:
                    plan.warnings.append(f"{s.mode}: temp {s.temperature_c}°C out of range {lo}-{hi}; clamped.")
                    s.temperature_c = min(max(s.temperature_c, lo), hi)

            # Attachment presence
            if s.attachment and s.attachment not in profile.attachments:
                plan.warnings.append(f"Attachment '{s.attachment}' not in robot profile attachments list.")
        return plan
