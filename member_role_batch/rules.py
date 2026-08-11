from __future__ import annotations

from io import BytesIO
from typing import Optional

import discord
from PIL import Image

from .config import AutoRoleBatchConfig

_AVATAR_CACHE: dict[str, bytes] = {}
_AVATAR_CACHE_MAX = 10_000
_AVATAR_READ_SIZE = 256

# 巨大画像によるメモリ枯渇(Decompression Bomb)を防ぐためのピクセル上限
# 256x256 のアバター解析には十分大きく、数億ピクセルの不正画像を弾く。
Image.MAX_IMAGE_PIXELS = 4_096 * 4_096


def _cache_avatar(key: str, data: bytes) -> bytes:
    if len(_AVATAR_CACHE) >= _AVATAR_CACHE_MAX:
        _AVATAR_CACHE.clear()
    _AVATAR_CACHE[key] = data
    return data


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

    cache_key = f"{member.id}:{avatar.key}"
    avatar_bytes = _AVATAR_CACHE.get(cache_key)
    if avatar_bytes is None:
        try:
            # 小さいサイズ(256px)のみを取得し、CDN転送量とデコード負荷を削減
            avatar_bytes = _cache_avatar(cache_key, await avatar.read(size=_AVATAR_READ_SIZE))
        except Exception as exc:
            return False, None, None, f"avatar_read_error:{exc}"

    try:
        black_ratio, transparent_ratio = get_icon_ratios(avatar_bytes, config)
        is_match = (
            black_ratio >= config.black_ratio_threshold
            or transparent_ratio >= config.transparent_ratio_threshold
        )
        return is_match, black_ratio, transparent_ratio, None
    except Image.DecompressionBombError as exc:
        return False, None, None, f"avatar_too_large:{exc}"
    except Exception as exc:
        return False, None, None, f"avatar_parse_error:{exc}"


async def should_assign_role(member: discord.Member, config: AutoRoleBatchConfig) -> bool:
    keyword_ok = has_target_keyword(member, config.target_id_keyword)
    if not keyword_ok:
        return False
    icon_ok, _, _, _ = await has_black_or_transparent_avatar(member, config)
    return icon_ok
