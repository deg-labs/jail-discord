import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AutoRoleBatchConfig:
    target_role_name: str = "testrole"
    target_id_keyword: str = "deg5"
    excluded_user_ids: frozenset[int] = frozenset()
    interval_minutes: int = 5
    black_luminance_threshold: int = 8
    black_ratio_threshold: float = 0.98
    transparent_alpha_threshold: int = 16
    transparent_ratio_threshold: float = 0.98
    verbose_logging: bool = True

    @classmethod
    def from_env(cls) -> "AutoRoleBatchConfig":
        raw_excluded = os.getenv("AUTO_ROLE_EXCLUDED_USER_IDS", "")
        excluded_ids: set[int] = set()
        for value in raw_excluded.split(","):
            item = value.strip()
            if not item:
                continue
            if item.isdigit():
                excluded_ids.add(int(item))
        return cls(
            target_role_name=os.getenv("AUTO_ROLE_TARGET_ROLE", "testrole"),
            target_id_keyword=os.getenv("AUTO_ROLE_TARGET_KEYWORD", "deg5"),
            excluded_user_ids=frozenset(excluded_ids),
            interval_minutes=max(1, int(os.getenv("AUTO_ROLE_INTERVAL_MINUTES", "5"))),
            black_luminance_threshold=max(
                0, min(255, int(os.getenv("AUTO_ROLE_BLACK_LUMINANCE_THRESHOLD", "8")))
            ),
            black_ratio_threshold=max(
                0.0, min(1.0, float(os.getenv("AUTO_ROLE_BLACK_RATIO_THRESHOLD", "0.98")))
            ),
            transparent_alpha_threshold=max(
                0, min(255, int(os.getenv("AUTO_ROLE_TRANSPARENT_ALPHA_THRESHOLD", "16")))
            ),
            transparent_ratio_threshold=max(
                0.0,
                min(1.0, float(os.getenv("AUTO_ROLE_TRANSPARENT_RATIO_THRESHOLD", "0.98"))),
            ),
            verbose_logging=os.getenv("AUTO_ROLE_VERBOSE_LOGGING", "true").lower() in ("1", "true", "yes", "on"),
        )
