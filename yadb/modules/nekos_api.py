import urllib
from typing import Any

import aiohttp
import discord
import yadb
from discord.ext import commands


class RequestsApi:
    base_url = 'https://nekos.life/api/v2'
    session = aiohttp.ClientSession()

    @staticmethod
    async def get(endpoint: str) -> Any:
        async with RequestsApi.session.get(f'{RequestsApi.base_url}/{endpoint}') as resp:
            return await resp.json()


VALID_TAGS = [
    'feet', 'yuri', 'trap', 'futanari', 'hololewd', 'lewdkemo',
    'solog', 'feetg', 'cum', 'erokemo', 'les', 'wallpaper', 'lewdk',
    'ngif', 'tickle', 'lewd', 'feed', 'gecg', 'eroyuri', 'eron',
    'cum_jpg', 'bj', 'nsfw_neko_gif', 'solo', 'kemonomimi', 'nsfw_avatar',
    'gasm', 'poke', 'anal', 'slap', 'hentai', 'avatar', 'erofeet', 'holo',
    'keta', 'blowjob', 'pussy', 'tits', 'holoero', 'lizard', 'pussy_jpg',
    'pwankg', 'classic', 'kuni', 'waifu', 'pat', '8ball', 'kiss', 'femdom',
    'neko', 'spank', 'cuddle', 'erok', 'fox_girl', 'boobs', 'random_hentai_gif',
    'smallboobs', 'hug', 'ero', 'smug', 'goose', 'baka'
]


async def setup(bot: yadb.Bot):
    bot.add_command(owoify)
    bot.add_command(eightball)
    bot.add_command(cat)
    bot.add_command(textcat)
    bot.add_command(why)
    bot.add_command(fact)
    bot.add_command(neko)


@commands.command()
async def owoify(ctx: yadb.Context, *, text: str) -> None:
    """owoификация."""

    escaped_text = urllib.parse.quote(text)

    resp = await RequestsApi.get(f'owoify?text={escaped_text}')

    await ctx.send_notification(resp['owo'])


@commands.command(name='8ball', hidden=True)
async def eightball(ctx: yadb.Context) -> None:
    resp = await RequestsApi.get('8ball')

    title = resp['response']
    url = resp['url']

    embed = yadb.Embed()
    embed.title = title
    embed.set_image(url=url)

    await ctx.reply(embed=embed)


@commands.command()
async def cat(ctx: yadb.Context) -> None:
    """случайное фото с кошечками."""

    resp = await RequestsApi.get('img/meow')

    url = resp['url']

    embed = yadb.Embed()
    embed.set_image(url=url)

    await ctx.reply(embed=embed)


@commands.command()
async def textcat(ctx: yadb.Context) -> None:
    """случайная текстовая кошечка."""

    resp = await RequestsApi.get('cat')

    cat = f'```\n{resp["cat"]}\n```'

    embed = yadb.Embed()
    embed.description = cat

    await ctx.reply(embed=embed)


@commands.command(hidden=True)
async def why(ctx: yadb.Context) -> None:
    resp = await RequestsApi.get('why')

    text = resp['why'].capitalize()

    if not text.endswith('.'):
        text += '.'

    await ctx.send_notification(text)


@commands.command(hidden=True)
async def fact(ctx: yadb.Context) -> None:
    resp = await RequestsApi.get('fact')

    text = resp['fact'].capitalize()

    if not text.endswith('.'):
        text += '.'

    await ctx.send_notification(text)


@commands.command()
@commands.is_nsfw()
async def neko(ctx: yadb.Context, tag: str) -> None:
    """неко!"""

    query = tag.lower()

    if query not in VALID_TAGS:
        raise ValueError("Invalid tag.")

    if query == 'random_hentai_gif':
        query = query.capitalize()

    resp = await RequestsApi.get('img/{}'.format(query))

    url = resp['url']

    embed = yadb.Embed()
    embed.set_image(url=url)

    await ctx.reply(embed=embed)


@neko.error
async def error_handler(ctx: yadb.Context, error: discord.DiscordException):
    async def send_tag_list():
        tags = f'```\n{" ".join(VALID_TAGS)}\n```'

        embed = yadb.Embed()
        embed.title = 'Список допустимых тегов'
        embed.description = tags
        embed.colour = discord.Colour.red()

        await ctx.reply(embed=embed)

    if isinstance(error, commands.MissingRequiredArgument):
        await send_tag_list()
    elif hasattr(error, 'original') and isinstance(error.original, ValueError):
        await send_tag_list()
