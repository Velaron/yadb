import ast
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout

import discord
import git
import psutil
import yadb
from discord.ext import commands


async def setup(bot: yadb.Bot):
    bot.add_command(restart)
    bot.add_command(_eval)
    bot.add_command(stats)

    if not yadb.config.has_section('Restart'):
        return

    channel_id = yadb.config.getint('Restart', 'ChannelId')
    message_id = yadb.config.getint('Restart', 'MessageId')

    yadb.config.remove_section('Restart')
    bot.write_config()

    channel = bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    ctx = await bot.get_context(message)
    await ctx.send_notification('Бот перезапущен.')


@commands.command(hidden=True)
@commands.is_owner()
async def restart(ctx: yadb.Context) -> None:
    # store channel in config
    yadb.config.add_section('Restart')
    yadb.config.set('Restart', 'ChannelId', str(ctx.channel.id))
    yadb.config.set('Restart', 'MessageId', str(ctx.message.id))
    ctx.bot.write_config()

    timestamp = os.path.getmtime('requirements.txt')

    # pull changes from git
    repo = git.Repo(os.getcwd())
    repo.remotes.origin.pull()

    # update dependencies
    if os.path.getmtime('requirements.txt') != timestamp:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U', '-r', 'requirements.txt'])

    # restart
    os.execl(sys.executable, sys.executable, *sys.argv)


@commands.command(hidden=True, name='eval')
@commands.is_owner()
async def _eval(ctx: yadb.Context, *, code: str) -> None:
    env = {
        'ctx': ctx,
        'discord': discord,
        'commands': commands,
        'yadb': yadb,
        '__import__': __import__
    }

    code = code[3:-3]
    code = '\n'.join('    {}'.format(x) for x in code.splitlines())
    code = 'async def _eval_():\n{}'.format(code)
    code = ast.parse(code)
    code = compile(code, filename='<ast>', mode='exec')
    exec(code, env)

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        result = await env['_eval_']()

    if result is None:
        val = stdout.getvalue()
        if len(val) > 0:
            await ctx.send('```\n{}\n```'.format(val))
    elif len(result) > 0:
        await ctx.send('```\n{}\n```'.format(result))


@commands.command(hidden=True)
@commands.is_owner()
async def stats(ctx: yadb.Context) -> None:
    embed = yadb.Embed()
    embed.title = 'Статистика'

    cpu_percent = psutil.cpu_percent(interval=1.0, percpu=True)
    cpu_count = psutil.cpu_count()
    cpu_usage = '\n'.join([f'Core {x + 1}: {cpu_percent[x]}%' for x in range(cpu_count)])
    embed.add_field(name='CPU', value=cpu_usage, inline=False)

    virtual_memory = psutil.virtual_memory()
    memory_used = virtual_memory.used / 1024 / 1024
    memory_total = virtual_memory.total / 1024 / 1024
    memory_usage = f'{memory_used:.1f}M/{memory_total:.1f}M ({virtual_memory.percent}%)'
    embed.add_field(name='RAM', value=memory_usage, inline=False)

    process_info = psutil.Process(os.getpid())
    process_usage = (
        f'CPU: {process_info.cpu_percent()}%\n'
        f'RAM: {process_info.memory_percent():.1f}%'
    )
    embed.add_field(name='Python', value=process_usage, inline=False)

    await ctx.reply(embed=embed)
