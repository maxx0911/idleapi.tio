from typing import Union

from discord.ext import commands


class NotInRange(commands.BadArgument):
    def __init__(self, text, from_, to_):
        self.text = text
        self.from_ = from_
        self.to_ = to_


class IntFromTo(commands.Converter):
    def __init__(self, from_, to_):
        self.from_ = from_
        self.to_ = to_

    async def convert(self, ctx, arg):
        try:
            arg = int(arg)
        except ValueError:
            raise commands.BadArgument("Converting to int failed.")
        if not self.from_ <= arg <= self.to_:
            raise NotInRange(
                "The supplied number must be in range of "
                f"{self.from_} to {self.to_}.",
                self.from_,
                self.to_,
            )
        return arg


class IntAboveZero(commands.Converter):
    async def convert(self, ctx, arg):
        try:
            arg = int(arg)
        except ValueError:
            raise commands.BadArgument("Converting to int failed.")
        if not arg >= 0:
            raise commands.BadArgument("Please choose a number above zero.")

        return arg
