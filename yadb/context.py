import re
from typing import Optional

import discord
from discord.ext import commands

import yadb


class Context(commands.Context):
    bot: 'yadb.Bot'

    async def send_error(self, error: Optional[str]) -> discord.Message:
        embed = yadb.Embed()

        embed.title = ':warning: Ошибка!'
        embed.description = error
        embed.colour = discord.Colour.brand_red()

        return await self.reply(embed=embed)

    async def send_notification(self, message: Optional[str]) -> discord.Message:
        embed = yadb.Embed()

        embed.description = message

        return await self.reply(embed=embed)

    async def reply(self, content: Optional[str] = None, **kwargs) -> discord.Message:
        return await super().reply(content, mention_author=False, **kwargs)

    def strip_ansi(self, s: str) -> str:
        return re.sub(r'\x1b\[([0-9,A-Z]{1,2}(;[0-9]{1,2})?(;[0-9]{3})?)?[m|K]?', '', s)
