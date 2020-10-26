import discord
from discord.ext import commands


class NotAuthorized(commands.CheckFailure):
    """Exception raised when a user tries to use API commands without authorization"""

    def __init__(self, timer):
        self.timer = timer

    pass


class AlreadyAuthorized(commands.CheckFailure):
    """Exception raised when a user is already authorized."""

    pass


class NotInDM(commands.CheckFailure):
    """Exception raised when a command is not used in private messages."""

    pass


class CommandInDevelopment(commands.CheckFailure):
    """Exception raised when a command is disabled for a standard user."""

    pass


class ApiIsDead(commands.CommandError):
    """error starting with 5"""

    def __init__(self, timer):
        self.timer = timer

    pass


def only_dm():
    """Checks if a command is used in private messages"""

    async def predicate(ctx):
        if not ctx.guild:
            return True
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        raise NotInDM("This command can only be used in private messages.")

    return commands.check(predicate)


def has_pro():
    """Checks if a user is in the items table and adds them, if not"""

    async def predicate(ctx):
        if not await ctx.bot.pool.fetchval(
            'SELECT EXISTS(SELECT 1 FROM items WHERE "user"=$1);',
            ctx.author.id,
        ):
            await ctx.bot.pool.execute(
                'INSERT INTO items ("user", protected) VALUES ($1, $2);',
                ctx.author.id,
                [],
            )
        return True

    return commands.check(predicate)


def dev():
    """Marks a command as 'in development'."""

    async def predicate(ctx):
        if ctx.author.id != 262133866062413825:
            raise CommandInDevelopment()
        return True

    return commands.check(predicate)
