import logging
from configparser import ConfigParser

from .context import Context
from .bot import Bot
from .embed import Embed
from .help import HelpCommand

config: ConfigParser = ConfigParser()
logger: logging.Logger = logging.getLogger('discord')
bot: Bot = Bot()
