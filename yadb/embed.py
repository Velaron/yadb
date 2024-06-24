import discord


class Embed(discord.Embed):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(colour=discord.Colour.teal(), *args, **kwargs)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = self._truncate_string(value, 256)
    
    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = self._truncate_string(value, 4096)

    # def to_dict(self) -> EmbedData:
        #self.title = self._truncate_string(self.title, 256)
        #self.description = self._truncate_string(self.description, 4096)
        #self.fields = self.fields[:25]

        # for f in self.fields:
        #    f.name = self._truncate_string(f.name, 256)
        #    f.value = self._truncate_string(f.value, 1024)

        #self.footer.text = self._truncate_string(self.footer.text, 2048)
        #self.author.name = self._truncate_string(self.author.name, 256)

        # while len(self) > 6000:
        #     self.remove_field(len(self.fields) - 1)

    #    return super().to_dict()

    # def set_channel(self, channel):
    #     if isinstance(channel, discord.DMChannel):
    #         name = '@{}'.format(channel.recipient)
    #     else:
    #         name = '#{}'.format(channel.name)

    #     self.set_footer(text='{} · {}'.format(name, self.timestamp()))
    #     self.ctx_channel = channel

    # def _timestamp(self) -> str:
     #   return datetime.now(pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y %H:%M:%S')

    def _truncate_string(self, string: str, length: int) -> str:
        if string and len(string) > length:
            return f'{string[:length-3]}...'

        return string
