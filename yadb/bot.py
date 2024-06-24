import logging
import os

import colorlog
import discord
from discord import Intents
from discord.ext import commands

import yadb


class Bot(commands.Bot):
    def __init__(self) -> None:
        # set up logging
        self._setup_logging()

        # load configuration file
        self._load_config()

        prefix = yadb.config.get('Discord', 'Prefix')

        super().__init__(command_prefix=commands.when_mentioned_or(prefix),
                         intents=Intents.all(),
                         case_insensitive=True,
                         help_command=yadb.HelpCommand(),
                         activity=self._get_activity())

    async def setup_hook(self) -> None:
        self.add_listener(self.on_ready, 'on_ready')

        # load user modules
        await self._load_modules()

        guild_id = yadb.config.get('Discord', 'Guild')
        synced = await self.tree.sync(guild=discord.Object(id=guild_id))
        yadb.logger.info(f'Synced {len(synced)} commands.')

    def run(self, *args, **kwargs) -> None:
        token = yadb.config.get('Discord', 'Token')

        super().run(token, log_handler=None, *args, **kwargs)

    async def _load_modules(self) -> None:
        files = os.listdir(os.path.join('yadb', 'modules'))

        for file in files:
            if not file.endswith('.py'):
                continue

            filename = file.split(".")[0]

            try:
                ext = f'yadb.modules.{filename}'
                await self.load_extension(ext)
            except Exception as e:
                yadb.logger.error(f'Loading extension [{filename}] failed!')
                raise e
            else:
                yadb.logger.info(f'Loading extension [{filename}] successful.')

    def _load_config(self) -> None:
        yadb.logger.info('Loading config...')

        yadb.config.optionxform = str
        yadb.config.read('config.ini')

        # if not price.config.has_section('Discord'):
        #     price.config.add_section('Discord')

        # with open('config.ini', 'w') as f:
        #     price.config.write(f)

        # # TODO: make this less ugly
        # for key in ['Token', 'Prefix']:
        #     if not price.config.has_option('Discord', key):
        #         price.logger.error(f'Missing value in config: {key}')
        #         # TODO: stop execution?

    def _setup_logging(self) -> None:
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            fmt='%(log_color)s[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%d.%m.%Y %H:%M:%S'
        ))

        yadb.logger.setLevel(logging.INFO)
        yadb.logger.addHandler(handler)

    def _get_activity(self):
        prefix = yadb.config.get('Discord', 'Prefix')

        activity = discord.Activity()
        activity.type = discord.ActivityType.listening
        activity.name = f'{prefix}help'

        return activity

        # await self.change_presence(status=discord.Status.online, activity=activity)

    def write_config(self) -> None:
        with open('config.ini', 'w') as f:
            yadb.config.write(f)

    def _print_invite_link(self):
        invite_link = discord.utils.oauth_url(
            self.user.id,
            permissions=discord.Permissions().all()
        )
        yadb.logger.info(f'Invite link: {invite_link}.')

    async def on_ready(self) -> None:
        # set activity status
        # await self._set_activity()

        self._print_invite_link()

        yadb.logger.info(f'Bot [{self.user}] successfully connected.')

    async def get_context(self, message, *, cls=yadb.Context):
        return await super().get_context(message, cls=cls)

    async def on_command_error(self, ctx: yadb.Context, error: discord.DiscordException) -> None:
        if isinstance(error, commands.NSFWChannelRequired):
            # logging.error('NSFW request in non-NSFW channel.')
            await ctx.send_error('Для выполнения команды необходим NSFW канал')
        elif isinstance(error, commands.NotOwner):
            # logging.error('The command is owner-only.')
            await ctx.send_error('Команда доступна только владельцу')
        elif isinstance(error, commands.MissingPermissions):
            # logging.error('User missing permissions.')
            await ctx.send_error('У вас нет доступа для использования команды')
        elif isinstance(error, commands.BotMissingPermissions):
            # logging.error('Bot missing permissions.')
            await ctx.send_error('У меня нет доступа для использования этой команды')
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            return
        else:
            raise error
