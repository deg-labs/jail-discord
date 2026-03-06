from __future__ import annotations

import asyncio
import time
from typing import Optional

import discord
from discord.ext import tasks

from .config import AutoRoleBatchConfig
from .rules import has_black_or_transparent_avatar, has_target_keyword


class AutoRoleBatchService:
    def __init__(self, bot: discord.Client, config: Optional[AutoRoleBatchConfig] = None):
        self.bot = bot
        self.config = config or AutoRoleBatchConfig.from_env()
        self._loop.start()

    def stop(self) -> None:
        if self._loop.is_running():
            self._loop.cancel()

    @tasks.loop(minutes=5)
    async def _loop(self) -> None:
        await self.run_cycle()

    @_loop.before_loop
    async def _before_loop(self) -> None:
        await self.bot.wait_until_ready()
        self._loop.change_interval(minutes=self.config.interval_minutes)
        print(
            "[auto-role] loop started "
            f"interval={self.config.interval_minutes}m "
            f"target_role={self.config.target_role_name} "
            f"keyword={self.config.target_id_keyword} "
            f"excluded_user_count={len(self.config.excluded_user_ids)} "
            f"black_ratio_threshold={self.config.black_ratio_threshold} "
            f"transparent_ratio_threshold={self.config.transparent_ratio_threshold} "
            f"luminance_threshold={self.config.black_luminance_threshold} "
            f"alpha_threshold={self.config.transparent_alpha_threshold} "
            f"verbose={self.config.verbose_logging}"
        )
        print("[auto-role] initial scan start")
        await self.run_cycle()

    async def run_cycle(self) -> None:
        guilds = list(self.bot.guilds)
        if not guilds:
            print("[auto-role] no guilds joined")
            return

        started = time.monotonic()
        print(f"[auto-role] cycle start guild_count={len(guilds)}")
        for guild in guilds:
            await self._process_guild(guild)
        elapsed = time.monotonic() - started
        print(f"[auto-role] cycle done elapsed={elapsed:.2f}s")

    async def _process_guild(self, guild: discord.Guild) -> None:
        role = discord.utils.get(guild.roles, name=self.config.target_role_name)
        if role is None:
            print(f"[auto-role] role not found: guild={guild.id} role={self.config.target_role_name}")
            return

        me = guild.me
        if me is None and self.bot.user:
            me = guild.get_member(self.bot.user.id)
        if me is None:
            print(f"[auto-role] bot member not found in guild={guild.id}")
            return

        manage_roles = me.guild_permissions.manage_roles
        top_role_pos = me.top_role.position if me.top_role else -1
        role_pos = role.position
        can_manage_role = top_role_pos > role_pos
        print(
            "[auto-role] guild check "
            f"guild={guild.id} "
            f"manage_roles={manage_roles} "
            f"bot_top_role={me.top_role.name if me.top_role else 'none'}({top_role_pos}) "
            f"target_role={role.name}({role_pos}) "
            f"can_manage_target_role={can_manage_role}"
        )
        if not manage_roles:
            print(f"[auto-role] skip guild={guild.id} reason=missing_manage_roles_permission")
            return
        if not can_manage_role:
            print(f"[auto-role] skip guild={guild.id} reason=role_hierarchy_invalid")
            return

        stats = {
            "fetched": 0,
            "bots": 0,
            "excluded": 0,
            "already": 0,
            "keyword_only": 0,
            "avatar_only": 0,
            "both_match": 0,
            "no_match": 0,
            "eligible": 0,
            "added": 0,
            "failed": 0,
        }
        try:
            async for member in guild.fetch_members(limit=None):
                stats["fetched"] += 1
                await self._process_member(member, role, stats)
        except Exception as exc:
            print(f"[auto-role] member fetch failed: guild={guild.id} error={exc}")
            return

        print(
            "[auto-role] guild summary "
            f"guild={guild.id} fetched={stats['fetched']} bots={stats['bots']} excluded={stats['excluded']} already={stats['already']} "
            f"keyword_only={stats['keyword_only']} avatar_only={stats['avatar_only']} both_match={stats['both_match']} no_match={stats['no_match']} "
            f"eligible={stats['eligible']} added={stats['added']} failed={stats['failed']}"
        )

    async def _process_member(
        self, member: discord.Member, role: discord.Role, stats: dict[str, int]
    ) -> None:
        if member.bot:
            stats["bots"] += 1
            if self.config.verbose_logging:
                print(f"[auto-role] skip user={member.id} reason=bot")
            return
        if member.id in self.config.excluded_user_ids:
            stats["excluded"] += 1
            if self.config.verbose_logging:
                print(f"[auto-role] skip user={member.id} reason=excluded_user")
            return
        if role in member.roles:
            stats["already"] += 1
            if self.config.verbose_logging:
                print(f"[auto-role] skip user={member.id} reason=already_has_role")
            return

        icon_ok, black_ratio, transparent_ratio, avatar_error = await has_black_or_transparent_avatar(
            member, self.config
        )
        keyword_ok = has_target_keyword(member, self.config.target_id_keyword)

        if keyword_ok and icon_ok:
            stats["both_match"] += 1
        elif keyword_ok:
            stats["keyword_only"] += 1
        elif icon_ok:
            stats["avatar_only"] += 1
        else:
            stats["no_match"] += 1
            if self.config.verbose_logging:
                print(
                    "[auto-role] skip "
                    f"user={member.id} "
                    f"name={member.name} "
                    f"display={member.display_name} "
                    f"reason=no_or_match "
                    f"keyword={self.config.target_id_keyword} "
                    f"keyword_ok={keyword_ok} "
                    f"icon_ok={icon_ok} "
                    f"black_ratio={black_ratio} "
                    f"transparent_ratio={transparent_ratio} "
                    f"required_ratio={self.config.black_ratio_threshold} "
                    f"required_transparent_ratio={self.config.transparent_ratio_threshold} "
                    f"error={avatar_error}"
                )
            return

        if self.config.verbose_logging:
            print(
                "[auto-role] eligible "
                f"user={member.id} "
                f"name={member.name} "
                f"display={member.display_name} "
                f"or_match keyword_ok={keyword_ok} icon_ok={icon_ok} "
                f"black_ratio={black_ratio} transparent_ratio={transparent_ratio}"
            )
        stats["eligible"] += 1

        try:
            await member.add_roles(
                role,
                reason="Auto role batch: keyword match OR black icon",
            )
            stats["added"] += 1
            print(
                "[auto-role] role added "
                f"guild={member.guild.id} user={member.id} "
                f"name={member.name} display={member.display_name} black_ratio={black_ratio}"
            )
        except Exception as exc:
            stats["failed"] += 1
            print(
                "[auto-role] role add failed "
                f"guild={member.guild.id} user={member.id} error={exc}"
            )
