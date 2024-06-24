import asyncio
import math
from time import gmtime, strftime

import discord
import aiohttp

import yadb
import yt_dlp
from discord.ext import commands

yt_dlp.utils.bug_reports_message = lambda: ''

YTDL_PARAMS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_PARAMS = {
    'before_options': '-loglevel quiet -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

DEFAULT_VOLUME = 10
SONGS_PER_PAGE = 10
TIMEOUT_SECONDS = 60

youtube_dl = yt_dlp.YoutubeDL(YTDL_PARAMS)


class VkApi:
    base_url = 'https://api.vk.com/method'
    session = aiohttp.ClientSession()
    user_agent = ('VKAndroidApp/5.52-4543 '
                  '(Android 5.1.1; SDK 22; x86_64; unknown Android SDK built for x86_64; en; 320x240)')
    access_token = yadb.config.get('VK', 'AccessToken')

    @staticmethod
    async def call(method: str, specparam: dict[str, str]):
        param = {'v': '5.116', 'access_token': VkApi.access_token}
        param.update(specparam)
        async with VkApi.session.post(f'{VkApi.base_url}/{method}', data=param,
                                      headers={'User-Agent': VkApi.user_agent}) as resp:
            return await resp.json()


async def setup(bot: yadb.Bot):
    await bot.add_cog(Music())


def teardown(bot: yadb.Bot):
    async def _disconnect_players():
        for p in Player.instances:
            await p.disconnect()

    bot.loop.create_task(_disconnect_players())


class Song(discord.PCMVolumeTransformer):
    title: str
    url: str
    duration: str
    thumbnail: str
    source: str
    mention: str

    def __init__(self, volume: float, **options):
        self.title = options.get('title')
        self.url = options.get('url')
        self.duration = options.get('duration')
        self.thumbnail = options.get('thumbnail')
        self.source = options.get('source')
        self.mention = options.get('mention')

        super().__init__(discord.FFmpegPCMAudio(self.url, **FFMPEG_PARAMS), volume=volume)

    @property
    def info(self) -> str:
        return f'{self.duration} · [ссылка]({self.source}) · добавлено {self.mention}'

    @property
    def info_short(self) -> str:
        return f'{self.duration} · [ссылка]({self.source})'

    def get_embed(self) -> yadb.Embed:
        embed = yadb.Embed()
        embed.title = ':arrow_forward: Воспроизведение'
        embed.add_field(name=self.title, value=self.info, inline=False)

        if self.thumbnail:
            embed.set_image(url=self.thumbnail)

        return embed


class YtSong(Song):
    def __init__(self, data: dict[str, str], mention: str, volume: float) -> None:
        super().__init__(
            volume=volume,
            title=data['title'],
            url=data['url'],
            duration=strftime('%H:%M:%S', gmtime(data['duration'])),
            thumbnail=data['thumbnail'],
            source=data['webpage_url'],
            mention=mention
        )


class VkSong(Song):
    @classmethod
    async def create(cls, data: dict[str, str], mention: str, volume: float):
        url = await VkSong.get_url(data)

        return cls(
            volume=volume,
            title=f'{data["artist"]} - {data["title"]}',
            url=url,
            duration=strftime('%H:%M:%S', gmtime(data['duration'])),
            thumbnail=VkSong.get_thumbnail(data),
            source=url,
            mention=mention
        )

    @staticmethod
    async def get_url(data: dict[str, str]) -> str:
        request = await VkApi.call('audio.getById', {'audios': f'{data["owner_id"]}_{data["id"]}_{data["access_key"]}'})
        url = request['response'][0]['url']

        if not url:
            raise ValueError('Access denied.')
        else:
            return url

    @staticmethod
    def get_thumbnail(data) -> str:
        if 'album' in data:
            if 'thumb' in data['album']:
                return list(data['album']['thumb'].values())[-1]
        else:
            return ''


class Player:
    id: int
    voice_client: discord.VoiceClient | discord.VoiceProtocol
    playing: Song | None
    queue: list[Song]
    selection: list[Song]
    ctx: yadb.Context
    volume: int
    timer: asyncio.Task | None

    instances: list['Player'] = []

    def __init__(self, guild: discord.Guild):
        self.id = guild.id
        self.voice_client = guild.voice_client
        self.playing = None
        self.queue = []
        self.volume = DEFAULT_VOLUME
        self.timer = None

    def is_empty(self) -> bool:
        return not self.queue

    def is_playing(self) -> bool:
        return self.playing is not None

    def is_paused(self) -> bool:
        return self.voice_client.is_paused()

    def toggle_pause(self) -> bool:
        if self.is_paused():
            self.voice_client.resume()
        else:
            self.voice_client.pause()

        return self.is_paused()

    def skip(self):
        self.voice_client.stop()

    @property
    def volume(self) -> float:
        return float(self._volume) / 100.0

    @volume.setter
    def volume(self, value: int):
        self._volume = value

    def next(self, error: Exception):
        async def _next():
            if len(self.queue) == 0:
                self.playing = None
                self.timer = asyncio.ensure_future(self.disconnect_timer())
                # await self.disconnect()
            else:
                await self.play()

        yadb.bot.loop.create_task(_next())

    async def disconnect_timer(self):
        await asyncio.sleep(TIMEOUT_SECONDS)
        await self.disconnect()

    async def disconnect(self):
        await self.voice_client.disconnect()
        Player.instances.remove(self)

    async def play(self, songs: list[Song] = None):
        if songs:
            self.queue += songs

        if self.voice_client.is_playing():
            return

        if self.voice_client.is_paused():
            return

        self.playing = self.queue.pop(0)
        self.voice_client.play(self.playing, after=self.next)

        await self.ctx.send(embed=self.playing.get_embed())

    @staticmethod
    def get(guild):
        for p in Player.instances:
            if p.id == guild.id:
                return p

        p = Player(guild)
        Player.instances.append(p)
        return p


class SongDropdown(discord.ui.Select):
    def __init__(self, player: Player, songs: list[Song]):
        super().__init__(placeholder='Выберите песню...', min_values=1, max_values=1)

        self.player = player
        self.songs = songs

        for i, s in enumerate(songs):
            self.add_option(label=s.title, value=str(i))

    async def callback(self, interaction: discord.Interaction):
        songs = [self.songs[int(self.values[0])]]

        embed = await Music.get_queue_embed(songs)
        await interaction.response.edit_message(view=None, embed=embed)

        await self.player.play(songs)


class SongDropdownView(discord.ui.View):
    def __init__(self, player: Player, songs: list[Song]):
        super().__init__()

        self.add_item(SongDropdown(player, songs))


class Music(commands.Cog, name='Музыка'):
    @commands.command(aliases=['p'])
    async def play(self, ctx: yadb.Context, *, url: str):
        """воспроизведение песни."""

        player = Player.get(ctx.guild)

        youtube_dl.params.update({'default_search': 'ytsearch1'})
        data = await self._get_yt_songs(url, loop=yadb.bot.loop, stream=True)

        entries = data.get('entries', [data])
        songs = [YtSong(e, ctx.author.mention, player.volume) for e in entries]

        if len(songs) == 0:
            await ctx.send_error('Ничего не найдено')
            return

        if not player.is_empty() or player.is_playing():
            embed = await Music.get_queue_embed(songs)
            await ctx.reply(embed=embed)

        await player.play(songs)

    @commands.command()
    async def pause(self, ctx: yadb.Context):
        """приостановка песни."""

        if not Player.get(ctx.guild).toggle_pause():
            await ctx.send_notification('Воспроизведение возобновлено')
        else:
            await ctx.send_notification('Воспроизведение приостановлено')

    @commands.command()
    async def search(self, ctx: yadb.Context, *, query: str):
        """поиск песен."""

        player = Player.get(ctx.guild)

        youtube_dl.params.update({'default_search': 'ytsearch10'})
        data = await self._get_yt_songs(query, loop=yadb.bot.loop, stream=True)
        songs = [YtSong(e, ctx.author.mention, player.volume) for e in data['entries']]

        await self.send_dropdown(ctx, player, songs, query)

    @commands.command()
    async def play_vk(self, ctx, *, url: str):
        """воспроизведение песни ВКонтакте."""

        player = Player.get(ctx.guild)

        data = await self._get_vk_songs(url, 1)
        songs = [await VkSong.create(e, ctx.author.mention, player.volume) for e in data]

        if len(songs) == 0:
            await ctx.send_error('Ничего не найдено')
            return

        if not player.is_empty() or player.is_playing():
            embed = await Music.get_queue_embed(songs)
            await ctx.reply(embed=embed)

        await player.play(songs)

    @commands.command()
    async def search_vk(self, ctx: yadb.Context, *, query: str):
        """поиск песен ВКонтакте."""

        player = Player.get(ctx.guild)

        data = await self._get_vk_songs(query, 10)
        songs = [await VkSong.create(e, ctx.author.mention, player.volume) for e in data]

        await self.send_dropdown(ctx, player, songs, query)

    @commands.command(aliases=['q', 'list'])
    async def queue(self, ctx: yadb.Context, page: int = 1):
        """очередь песен."""

        player = Player.get(ctx.guild)

        embed = yadb.Embed()

        total_songs = len(player.queue)
        total_pages = math.ceil(float(total_songs) / SONGS_PER_PAGE)

        if page < 1 or (page > total_pages and total_songs > 0):
            await ctx.send_error('Неправильная страница')
            return

        embed.title = ':musical_note: Сейчас играет'
        embed.add_field(name=player.playing.title, value=player.playing.info, inline=False)

        if total_songs > 0:
            prefix = yadb.config.get('Discord', 'Prefix')

            first_song = (page - 1) * SONGS_PER_PAGE
            last_song = min(first_song + SONGS_PER_PAGE, total_songs)

            embed.add_field(name=f'Композиций в очереди: {total_songs} [1 - {total_pages}]',
                            value=f'{prefix}queue *n* - просмотр страниц', inline=False)

            songs = player.queue[first_song:last_song]
            for i, s in enumerate(songs, start=first_song + 1):
                embed.add_field(name=f'{i}. {s.title}', value=s.info, inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=['s'])
    async def skip(self, ctx: yadb.Context, index: int = 1):
        """пропустить песню."""

        player = Player.get(ctx.guild)

        if index < 1 or (index > len(player.queue) and not player.is_playing()):
            await ctx.send_error('Неправильный номер песни')
            return

        if len(player.queue) == 0:
            song = player.playing
        else:
            song = player.queue[index - 1]

        embed = yadb.Embed()
        embed.title = ':track_next: Пропущено'
        embed.add_field(name=song.title, value=song.info, inline=False)

        if index == 1:
            player.skip()
        else:
            player.queue.remove(song)

        await ctx.reply(embed=embed)

    @commands.command()
    async def skip_to(self, ctx: yadb.Context, index: int):
        """перейти к песне в очереди."""

        player = Player.get(ctx.guild)

        if index < 1 or (index > len(player.queue) and not player.is_playing()):
            await ctx.send_error('Неправильный номер песни')
            return

        skipped = player.queue[:index - 1]

        embed = yadb.Embed()
        embed.title = 'Пропущено'

        for s in skipped:
            embed.add_field(name=s.title, value=s.info, inline=False)

        await ctx.send(embed=embed)

        player.queue = player.queue[index - 1:]
        player.skip()

    @commands.command(aliases=['v'])
    async def volume(self, ctx: yadb.Context, volume: int = None):
        """сменить громкость воспроизведения."""

        player = Player.get(ctx.guild)

        if volume is None:
            await ctx.send_notification(f'Текущая громкость: {player.volume}%')
            return

        if volume < 0:
            await ctx.send_error('Неправильное значение громкости')
            return

        player.volume = volume
        player.voice_client.source.volume = player.volume

        await ctx.send_notification(f'Громкость установлена: {volume}%')

    @commands.command()
    async def leave(self, ctx):
        """покинуть голосовой канал."""

        player = Player.get(ctx.guild)

        await player.disconnect()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        player = Player.get(member.guild)

        player.voice_client = member.guild.voice_client

    async def cog_before_invoke(self, ctx: yadb.Context):
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect(self_deaf=True)
            else:
                await ctx.send_error('Вы не в голосовом канале')
                raise commands.CommandError('User not connected to a voice channel.')
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

        player = Player.get(ctx.guild)
        player.ctx = ctx

        if player.timer:
            player.timer.cancel()

    @pause.before_invoke
    @queue.before_invoke
    @skip.before_invoke
    async def check_if_empty(self, ctx: yadb.Context):
        player = Player.get(ctx.guild)

        if player.is_empty() and not player.is_playing():
            await ctx.send_error('Ничего не проигрывается')
            raise commands.CommandError('No song is currently playing.')

    async def _get_yt_songs(self, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: youtube_dl.extract_info(url, download=not stream))

        return data

    async def _get_vk_songs(self, query, count):
        data = await VkApi.call('audio.search', {'q': query, 'sort': 2, 'count': count})
        data_ = await VkApi.call('audio.search', {'q': query, 'sort': 0, 'count': count})

        entries = data['response']['items']
        entries += [x for x in data_['response']['items'] if x not in entries]

        return entries[:count]

    async def cog_command_error(self, ctx: yadb.Context, error: Exception):
        if isinstance(error, commands.BadArgument):
            await ctx.send_error('Неверное число')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_error('Введите запрос для поиска')
        elif isinstance(error, discord.ClientException):
            await ctx.send_error('ОПЯТЬ У ЕБУЧЕГО ДИСКОРДА СЕРВАКИ НЕ РАБОТАЮТ СУКА')
        elif hasattr(error, 'original') and isinstance(error.original, yt_dlp.DownloadError):
            await ctx.send_error(
                f'Произошла ошибка во время поиска:\n{ctx.strip_ansi(error.original.msg)}'
            )
        else:
            raise error

    @staticmethod
    async def get_queue_embed(songs: list[Song]) -> yadb.Embed:
        embed = yadb.Embed()
        embed.title = ':musical_note: Добавлено в очередь'

        for s in songs:
            embed.add_field(name=s.title, value=s.info_short, inline=False)

        if len(songs) == 1 and songs[0].thumbnail:
            embed.set_image(url=songs[0].thumbnail)

        return embed

    @staticmethod
    def get_selection_embed(songs: list[Song], query: str) -> yadb.Embed:
        embed = yadb.Embed()
        embed.title = f'Поиск по запросу "{query}"'

        for i, s in enumerate(songs, start=1):
            embed.add_field(name=f'{i}. {s.title}', value=s.info_short, inline=False)

        if len(songs) == 1 and songs[0].thumbnail:
            embed.set_image(url=songs[0].thumbnail)

        return embed

    async def send_dropdown(self, ctx: yadb.Context, player: Player, songs: list[Song], query: str):
        if len(songs) == 0:
            await ctx.send_error('Ничего не найдено')
            return

        view = SongDropdownView(player, songs)
        embed = Music.get_selection_embed(songs, query)
        await ctx.send(embed=embed, view=view)
