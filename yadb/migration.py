import json
import os
from configparser import ConfigParser


def migrate_config() -> None:
	cfg = ConfigParser()
	cfg.optionxform = str

	with open(os.path.join('configs', 'discord.json')) as file:
		jsoncfg = json.load(file)

		cfg.add_section('Discord')
		cfg.add_section('VK')

		cfg.set('Discord', 'Token', jsoncfg.get('token', ''))
		cfg.set('Discord', 'Prefix', jsoncfg.get('prefix', ''))
		cfg.set('VK', 'AccessToken', jsoncfg.get('access_token', ''))
	
	with open(os.path.join('configs', 'danbooru.json')) as file:
		jsoncfg = json.load(file)

		cfg.add_section('Danbooru')

		cfg.set('Danbooru', 'Username', jsoncfg.get('username', ''))
		cfg.set('Danbooru', 'ApiKey', jsoncfg.get('api_key', ''))
	
	with open(os.path.join('configs', 'pixiv.json')) as file:
		jsoncfg = json.load(file)

		cfg.add_section('Pixiv')

		cfg.set('Pixiv', 'RefreshToken', jsoncfg.get('refresh_token', ''))
	
	with open('config.ini', 'w') as file:
		cfg.write(file)
