from __future__ import annotations

from io import BytesIO
from typing import Optional

import discord
from PIL import Image

from .config import AutoRoleBatchConfig


def has_target_keyword(member: discord.Member, keyword: str) -> bool:
    lowered = keyword.lower()
    if lowered in member.name.lower():
        return True
    if member.global_name and lowered in member.global_name.lower():
        return True
    if member.display_name and lowered in member.display_name.lower():
        return True
    return False


def get_icon_ratios(image_bytes: bytes, config: AutoRoleBatchConfig) -> tuple[float, float]:
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    pixels = image.getdata()
    total = len(pixels)
    if total == 0:
        return 0.0, 0.0

    black_count = 0
    transparent_count = 0
    black_threshold = config.black_luminance_threshold
    alpha_threshold = config.transparent_alpha_threshold
    for red, green, blue, alpha in pixels:
        if alpha <= alpha_threshold:
            transparent_count += 1
            continue
        luminance = int(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        if luminance <= black_threshold:
            black_count += 1

    return black_count / total, transparent_count / total


async def has_black_or_transparent_avatar(
    member: discord.Member, config: AutoRoleBatchConfig
) -> tuple[bool, Optional[float], Optional[float], Optional[str]]:
    avatar = member.display_avatar
    if not avatar:
        return False, None, None, "avatar_missing"

    try:
        avatar_bytes = await avatar.read()
    except Exception as exc:
        return False, None, None, f"avatar_read_error:{exc}"

    try:
        black_ratio, transparent_ratio = get_icon_ratios(avatar_bytes, config)
        is_match = (
            black_ratio >= config.black_ratio_threshold
            or transparent_ratio >= config.transparent_ratio_threshold
        )
        return is_match, black_ratio, transparent_ratio, None
    except Exception as exc:
        return False, None, None, f"avatar_parse_error:{exc}"


async def should_assign_role(member: discord.Member, config: AutoRoleBatchConfig) -> bool:
    keyword_ok = has_target_keyword(member, config.target_id_keyword)
    if not keyword_ok:
        return False
    icon_ok, _, _, _ = await has_black_or_transparent_avatar(member, config)
    return icon_ok
