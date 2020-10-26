import traceback
from datetime import timedelta

from utils.checks import *


class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            time = timedelta(seconds=int(error.retry_after))
            return await ctx.send("You are on cooldown! Try again in {0}.".format(time))
        elif isinstance(
            error, (commands.errors.UserInputError, commands.errors.BadUnionArgument)
        ):
            s = (
                "Looks like some of your input was incorrect... Check"
                f" `{ctx.prefix}help {ctx.invoked_with}` for details.\n"
            )
            if ctx.command.name == "merch":
                s += f"You might have mistaken this command for `{ctx.prefix}xmerch`."
            return await ctx.send(s)
        elif isinstance(error, ApiIsDead):
            return await ctx.send(
                f"The API returned a 5XX error code. This means it is currently not available."
                f" Please try again in {error.timer} seconds."
            )
        elif isinstance(error, commands.CheckFailure):
            if isinstance(error, CommandInDevelopment):
                return await ctx.send(
                    "This command is currently under construction. Sorry for the inconvenience!"
                )
            else:
                return await ctx.send(
                    "One of the command checks failed, please report to the dev."
                )
        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send("This command is disabled.")
        else:
            return await ctx.send(
                "Error while using this command!\n\n**{0}**: {1}\n```{2}```".format(
                    type(error.original).__name__,
                    error.original,
                    "\n".join(
                        [
                            x.replace("`", "\u200b`\u200b")
                            for x in traceback.format_tb(error.original.__traceback__)
                        ]
                    ),
                )
            )


def setup(bot):
    bot.add_cog(Errors(bot))
