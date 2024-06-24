from discord.ext import commands

import yadb


def command_name(cmd: commands.Command) -> str:
    aliases = f'({", ".join(cmd.aliases)})' if cmd.aliases else ''
    name = f'**{yadb.config.prefix}{cmd.name}{aliases}**'
    return name


def command_help(cmd: commands.Command) -> str:
    help = f'*{cmd.help}*' if cmd.help else '*описание отсуствует.*'
    return help


@commands.command(name='help', hidden=True)
async def bot_help(ctx, show_hidden: bool = False) -> None:
    def add_category(embed, name, commands, value=''):
        longest_cmd = max([len(command_name(x)) for x in commands])
        print(longest_cmd)

        for cmd in commands:
            cmd_name = command_name(cmd)
            cmd_help = command_help(cmd)
            # value += f'{cmd_name}:{(longest_cmd - len(cmd_name)) * "\t"}{cmd_help}\n'

        if not value:
            value = '**Пусто.**'

        embed.add_field(name=name, value=value, inline=False)

    embed = yadb.Embed(ctx.channel)
    embed.set_title('Список команд')
    add_category(embed, 'Основные', [
        x for x in ctx.bot.walk_commands() if not x.hidden and not x.cog_name])

    for name, cog in ctx.bot.cogs.items():
        add_category(
            embed, name, [x for x in cog.walk_commands() if not x.hidden])

    if show_hidden and await ctx.bot.is_owner(ctx.author):
        add_category(embed, 'Скрытые', [
            x for x in ctx.bot.walk_commands() if x.hidden])

    await embed.send()


class HelpCommand(commands.DefaultHelpCommand):
    def __init__(self, **options) -> None:
        super().__init__(**options)

        self.no_category = "Основные"

    def get_ending_note(self) -> str:
        command_name = self.invoked_with
        return (
            f"Используйте {self.context.clean_prefix}{command_name} <команда> чтобы получить больше информации.\n"
            f"Так же можно использовать {self.context.clean_prefix}{command_name} <категория> для дополнительной информации о категории."
        )
