from contextlib import suppress
from typing import Optional, Union

import discord
from discord.ext import commands


class NoChoice(commands.CommandInvokeError):
    pass


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bot = kwargs.pop("bot")
        self.db = self.bot.pool

    async def confirm(
        self,
        message: str,
        timeout: int = 20,
        user: Optional[Union[discord.User, discord.Member]] = None,
        emoji_no: discord.Emoji = None,
        emoji_yes: discord.Emoji = None,
    ) -> bool:
        emoji_no = emoji_no or self.bot.get_emoji(693082203093205012)
        emoji_yes = emoji_yes or self.bot.get_emoji(693082203013251093)

        emoji_no, emoji_yes = emoji_no or "❎", emoji_yes or "✅"
        # failsafe if the default emoji is not found

        user = user or self.author
        emojis = (emoji_no, emoji_yes)

        if user.id == self.bot.user.id:
            return False

        msg = await self.send(message)
        for emoji in emojis:
            await msg.add_reaction(emoji)

        def check(r: discord.Reaction, u: discord.User) -> bool:
            return u == user and r.emoji in emojis and r.message.id == msg.id

        async def cleanup() -> None:
            with suppress(discord.HTTPException):
                await msg.delete()

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=timeout
            )
        except TimeoutError:
            await cleanup()
            raise NoChoice("You did not choose anything.")

        await cleanup()

        return bool(emojis.index(reaction.emoji))
