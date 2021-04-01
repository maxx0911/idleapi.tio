import random

import discord
from discord.ext import commands

from utils import paginator


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def category_gen(self, ctx):
        categories = {}

        for command in set(self.bot.walk_commands()):
            cog = command.cog_name or "No Category"
            if cog not in categories:
                categories.update({cog: []})

        for command in set(ctx.bot.walk_commands()):
            if not command.hidden:
                cog = command.cog_name or "No Category"
                categories[cog].append(command)

        return categories

    async def commandMapper(self, ctx):
        pages = []

        for category, commands in (await self.category_gen(ctx)).items():
            if not commands:
                continue
            cog = self.bot.get_cog(category)
            if cog:
                category = f"**⚙️ {category} commands**"
            cmd_list = ", ".join(
                [
                    cmd.name + "*" if hasattr(cmd, "commands") else cmd.name
                    for cmd in commands
                    if not cmd.parents
                ]
            )
            if not cmd_list:
                continue
            embed = (
                discord.Embed(
                    color=0x7289DA, title="Commands", description=f"{category}"
                )
                .set_footer(
                    text=(
                        f"Type {ctx.prefix}help <command> for more help | Commands with"
                        " * at the end have subcommands"
                    ),
                    icon_url=ctx.author.avatar_url,
                )
                .add_field(name="**Commands:**", value=f"``{cmd_list}``")
            )
            pages.append(embed)
        await paginator.Paginator(
            extras=sorted(pages, key=lambda d: d.description)
        ).paginate(ctx)

    async def cogMapper(self, ctx, entity, cogname: str):
        try:
            cmd_list = ", ".join(
                [
                    cmd.name + "*" if hasattr(cmd, "commands") else cmd.name
                    for cmd in set(self.bot.walk_commands())
                    if not cmd.parents and cmd.cog_name == cogname
                ]
            )
            await ctx.send(
                embed=discord.Embed(
                    color=0x7289DA, title="Commands", description=f"**⚙️ {cogname}**"
                )
                .add_field(name="**Commands:**", value=f"``{cmd_list}``")
                .set_footer(
                    text=(
                        f"Type {ctx.prefix}help <command> for more help | Commands with"
                        " `*` at the end have subcommands"
                    ),
                    icon_url=ctx.author.avatar_url,
                )
            )
        except BaseException:
            await ctx.send(
                f":x: | **Command or category not found. Use {ctx.prefix}help**",
                delete_after=10,
            )

    @commands.command(hidden=True)
    async def help(self, ctx, *, command: str = None):
        """View Bot Help Menu"""
        if not command:
            await self.commandMapper(ctx)
        else:
            entity = self.bot.get_cog(command) or self.bot.get_command(command)
            if entity is None:
                if command.title() in self.bot.cogs.keys():
                    entity = self.bot.cogs[command.title()]
                else:
                    return await ctx.send(
                        ":x: | **Command or category not found. Use"
                        f" {ctx.prefix}help**",
                        delete_after=10,
                    )
            if isinstance(entity, commands.Command):
                usage = f"{ctx.prefix} {entity.name} {entity.usage or entity.signature}"
                # usage = ctx.prefix + entity.name + (entity.usage or f" {entity.signature}")
                entries = [
                    f"**:video_game: Command Usage**\n```ini\n{usage}```",
                    f"**Command Help**\n```\n{entity.help}```",
                ]
                if hasattr(entity, "commands"):  # has subcommands
                    subcommands = ", ".join(
                        [
                            sb_cmd.name + "*"
                            if hasattr(sb_cmd, "commands")
                            else sb_cmd.name
                            for sb_cmd in entity.commands
                        ]
                    )
                    entries.append(f"**Subcommands**\n```\n{subcommands}```")
                await paginator.Paginator(
                    title=f"Command: {entity.name}",
                    entries=entries,
                    length=1,
                    colour=random.randint(0x000000, 0xFFFFFF),
                ).paginate(ctx)
            else:
                await self.cogMapper(ctx, entity, command)


def setup(bot):
    bot.add_cog(Help(bot))
