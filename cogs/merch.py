import argparse
import asyncio
import shlex
from io import BytesIO
from typing import Union

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from utils.checks import dev, has_pro
from utils.paginator import Paginator


def chunks(iterable, size):
    """Yield successive n-sized chunks from an iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class Merch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_url(
        self,
        *,
        user: int,
        stat_upper: int = None,
        stat_lower: int = None,
        types: list = None,
        hands: list = None,
        value_lower: int = None,
        value_upper: int = None,
        id_upper: int = None,
        id_lower: int = None,
    ):
        base = f"https://public-api.travitia.xyz/idle/allitems?&select=id,inventory(equipped)&inventory.equipped=is.false&owner=eq.{user}"
        dmg, dfn = f"{base}&armor=eq.0", f"{base}&damage=eq.0"

        if stat_lower:
            dmg += f"&damage=gte.{stat_lower}"
            dfn += f"&armor=gte.{stat_lower}"

        if stat_upper:
            dmg += f"&damage=lte.{stat_upper}"
            dfn += f"&armor=lte.{stat_upper}"

        if types:
            dmg += f"&type=in.({','.join(types)})"
            dfn += f"&type=in.({','.join(types)})"

        if hands:
            dmg += f"&hand=in.({','.join(hands)})"
            dfn += f"&hand=in.({','.join(hands)})"

        if value_lower:
            dmg += f"&value=gte.{value_lower}"
            dfn += f"&value=gte.{value_lower}"

        if value_upper:
            dmg += f"&value=lte.{value_upper}"
            dfn += f"&value=lte.{value_upper}"

        if id_lower:
            dmg += f"&id=gte.{id_lower}"
            dfn += f"&id=gte.{id_lower}"

        if id_upper:
            dmg += f"&id=lte.{id_upper}"
            dfn += f"&id=lte.{id_upper}"

        return [dmg, dfn]

    @has_pro()
    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command(aliases=["favourite", "favorite", "fav"])
    async def protect(self, ctx, *ids: int):
        """Protect items so that they will not be included in merch searches.
        You can only protect your own items. If you merch search for someone else, their protected items will not appear."""
        if not ids:
            return await ctx.send("No item IDs given.")
        HINT = False
        ids = sorted(list(set(ids)))  # kill dupes
        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            "https://public-api.travitia.xyz/idle/allitems?select=owner,id&"
            f"id=in.({','.join([str(i) for i in ids])})",
            headers={"Authorization": self.bot.config.api_token},
        ) as r:
            if r.status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
            res = await r.json()
        ids_ = sorted([i["id"] for i in res if i["owner"] == ctx.author.id])
        if ids != ids_:
            HINT = True
        async with self.bot.pool.acquire() as conn:
            already_protected = (
                await conn.fetchval(
                    'SELECT protected FROM items WHERE "user"=$1;', ctx.author.id
                )
                or []
            )
            to_protect = list(set(already_protected + ids_))
            await conn.execute(
                'UPDATE items SET protected=$1 WHERE "user"=$2',
                to_protect,
                ctx.author.id,
            )
        await ctx.send(
            "Updated protected items. Use `< viewfav` to verify.{}".format(
                "\nPlease note that some of the items did not belong to you, so they haven't been added."
                if HINT
                else ""
            )
        )

    @has_pro()
    @commands.command(aliases=["unfavourite", "unfavorite", "unfav"])
    async def unprotect(self, ctx, *ids: int):
        """Remove one of your protected items, they can then appear in merch searches again."""
        if not ids:
            return await ctx.send("No item IDs given.")
        protected = await self.bot.pool.fetchval(
            'SELECT protected FROM items WHERE "user"=$1;', ctx.author.id
        )
        to_protect = list(set(protected) - set(ids))
        await self.bot.pool.execute(
            'UPDATE items SET protected=$1 WHERE "user"=$2;', to_protect, ctx.author.id
        )
        await ctx.send("Updated protected items. Use `< viewfav` to verify.")

    @has_pro()
    @commands.command()
    async def clearfav(self, ctx):
        """Clear your protected items list."""
        await self.bot.pool.execute(
            """UPDATE items SET protected='{}' WHERE "user"=$1;""", ctx.author.id
        )
        await ctx.send("Cleared your protected items list.")

    @has_pro()
    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command()
    async def viewfav(self, ctx):
        """View a list of your protected items."""
        items = await self.bot.pool.fetchval(
            'SELECT protected FROM items WHERE "user"=$1', ctx.author.id
        )
        if not items:
            return await ctx.send("No protected items!")

        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            "https://public-api.travitia.xyz/idle/allitems?select=name,id,armor,damage&"
            f"id=in.({','.join([str(i) for i in items])})",
            headers={"Authorization": self.bot.config.api_token},
        ) as r:
            if r.status != 200:
                if int(r.status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
            data = await r.json()

        extras = []
        chunkers = chunks(data, 5)
        for chunk in chunkers:
            e = discord.Embed(
                title="Protected items",
                color=discord.Color.blurple(),
            )
            for i in chunk:
                type_ = (
                    "damage" if i["damage"] else "defense",
                    i["damage"] if i["damage"] else i["armor"],
                )
                e.add_field(
                    name=i["name"],
                    value=f"With {type_[1]} {type_[0]} | ID: {i['id']}",
                    inline=False,
                )
            extras.append(e)
        await Paginator(extras=extras).paginate(ctx)

    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command(aliases=["merchant", "merchall"])
    async def merch(
        self,
        ctx,
        user: Union[discord.User, discord.Member, int] = None,
        upperbound: int = None,
        lowerbound: int = 0,
    ):
        """
        Get a string that can be pasted in a chat with IdleRPG that replicates the merchall command while using the
        merch command.
        This command assumes that the prefix for IdleRPG is $.
        [user] is a user. If not given, the command author is used.
        [lowerbound] and [upperbound] are optional arguments to limit the gathered item IDs to certain item's stats.
        """
        user = user or ctx.author

        if isinstance(user, (discord.User, discord.Member)):
            user = user.id
        elif isinstance(user, int):
            user = user
        else:
            raise commands.BadArgument(
                f"Could not convert {user} to discord.User or int."
            )

        exc = (
            await self.bot.pool.fetchval(
                'SELECT protected FROM items WHERE "user"=$1', ctx.author.id
            )
            or []
        )
        exc = [str(i) for i in exc]

        if (upperbound is not None) and not lowerbound:
            lowerbound = 0

        if (lowerbound is not None) and (upperbound is not None):
            upperbound, lowerbound = abs(upperbound), abs(lowerbound)
            if lowerbound > upperbound:
                await ctx.send(
                    f"`lowerbound ({lowerbound})` is larger than `upperbound"
                    f" ({upperbound})`; switching the values..."
                )

            querydamage = (
                f"https://public-api.travitia.xyz/idle/allitems?&select=id,inventory("
                f"equipped)&inventory.equipped=is.false&owner=eq.{user}&damage=gte.{lowerbound}&damage=lte."
                f"{upperbound}&armor=eq.0 "
            )
            queryarmor = (
                f"https://public-api.travitia.xyz/idle/allitems?&select=id,inventory("
                f"equipped)&inventory.equipped=is.false&owner=eq.{user}&armor=gte.{lowerbound}&armor=lte."
                f"{upperbound}&damage=eq.0 "
            )

            async with ctx.typing():
                await self.bot.check_for_error_500()
                async with self.bot.session.get(
                    querydamage, headers={"Authorization": self.bot.config.api_token}
                ) as r:
                    status = r.status
                    if status != 200:
                        if int(status / 100) == 5:
                            await self.bot.redis.execute(
                                "SET", f"travapi:520", "timeout", "EX", 3600
                            )
                            return await ctx.send(
                                "The API returned a 5XX error code. This means it is currently not available."
                                " Please try again in one hour."
                            )
                        elif status == 429:
                            return await ctx.send(
                                "429: Too many requests. The API only allows three"
                                " requests per ten seconds."
                            )
                    resdamage = await r.json()
                weaponlist = [str(item["id"]) for item in resdamage]
                await self.bot.check_for_error_500()
                async with self.bot.session.get(
                    queryarmor, headers={"Authorization": self.bot.config.api_token}
                ) as r:
                    if r.status != 200:
                        if int(r.status / 100) == 5:
                            await self.bot.redis.execute(
                                "SET", f"travapi:520", "timeout", "EX", 3600
                            )
                            return await ctx.send(
                                "The API returned a 5XX error code. This means it is currently not available."
                                " Please try again in one hour."
                            )
                    resarmor = await r.json()
                shieldlist = [str(item["id"]) for item in resarmor]
                itemlist = list(set(weaponlist + shieldlist) - set(exc))

        else:
            query = (
                f"https://public-api.travitia.xyz/idle/allitems?&select=id,inventory("
                f"equipped)&inventory.equipped=is.false&owner=eq.{user}"
            )
            async with ctx.typing():
                await self.bot.check_for_error_500()
                async with self.bot.session.get(
                    query, headers={"Authorization": self.bot.config.api_token}
                ) as r:
                    if r.status != 200:
                        if int(r.status / 100) == 5:
                            await self.bot.redis.execute(
                                "SET", f"travapi:520", "timeout", "EX", 3600
                            )
                            return await ctx.send(
                                "The API returned a 5XX error code. This means it is currently not available."
                                " Please try again in one hour."
                            )
                    res = await r.json()
                itemlist = list(
                    set([str(item["id"]) for item in res if item["inventory"]])
                    - set(exc)
                )

        if len(itemlist) == 0:
            return await ctx.send("No items to merch!")

        output = "```$merch {0}```".format(" ".join(itemlist[:150]))
        out = await ctx.send(output)
        if len(itemlist) > 150:
            await ctx.send(
                "This is not the complete list, but rather a shortened one to allow"
                " processing the command.",
                delete_after=10,
            )

        await out.add_reaction("\U0001F5D1")

        def recheck(r, u):
            return (
                str(r.emoji) == "\U0001F5D1"
                and r.message.id == out.id
                and u.id == ctx.author.id
                and not u.bot
            )

        try:
            await self.bot.wait_for("reaction_add", check=recheck, timeout=30)
            return await out.delete()
        except asyncio.TimeoutError:
            try:
                return await out.clear_reactions()
            except discord.Forbidden:
                await out.remove_reaction("\U0001F5D1", ctx.me)

    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command(aliases=["xmerchant", "xmerchall"])
    async def xmerch(self, ctx, *, args=None):
        """
        An alternative way to collect item IDs, based on different criteria.
        Please call < xmerch --help for details on usage.

        DISCLAIMER: This command is experimental. idleAPI.tio will not take responsibility for lost items.
        """
        if not args:
            return await ctx.send(
                "No arguments passed. Please take a look at `< xmerch --help`"
            )

        parser = Arguments(add_help=False, allow_abbrev=True)
        parser.add_argument("--help", action="store_true", help="Shows this message.")
        parser.add_argument(
            "-u",
            "--user",
            help=(
                "A Discord User, could be their tag or User ID. Defaults to the command"
                " author if not given."
            ),
        )
        parser.add_argument(
            "-hi",
            "--upper",
            type=int,
            default=0,
            help=(
                "The highest stat to include, this is inclusive. Should be an integer"
                " type. Defaults to 100."
            ),
        )
        parser.add_argument(
            "-lo",
            "--lower",
            type=int,
            default=0,
            help=(
                "The lowest stat to include, this is inclusive. Should be an integer"
                " type. Defaults to 0."
            ),
        )
        parser.add_argument(
            "-t",
            "--type",
            "--types",
            nargs="+",
            type=str.title,
            default=[],
            help=(
                "The item types to include. All types by default. Can be multiple (view"
                " examples page)."
            ),
        )
        parser.add_argument(
            "-h",
            "--hand",
            "--hands",
            nargs="+",
            type=str.lower,
            default=[],
            help=(
                "The item hands to include. All hands by default. Can be multiple (view"
                " examples page)."
            ),
        )
        parser.add_argument(
            "-vh",
            "--valueupper",
            type=int,
            default=0,
            help=(
                "The highest value to include, this is inclusive. Should be an integer"
                " type. Defaults to 10000."
            ),
        )
        parser.add_argument(
            "-vl",
            "--valuelower",
            type=int,
            default=0,
            help=(
                "The lowest value to include, this is inclusive. Should be an integer"
                " type. Defaults to 0."
            ),
        )
        parser.add_argument(
            "-idlo",
            "--idlower",
            type=int,
            default=0,
            help=(
                "The lowest item ID to include, this is inclusive. Should be an integer"
                " type. Defaults to 0."
            ),
        )
        parser.add_argument(
            "-idhi",
            "--idupper",
            type=int,
            default=0,
            help=(
                "The highest item ID to include, this is inclusive. Should be an"
                " integer type. Defaults to 100000000."
            ),
        )
        parser.add_argument(
            "-ex",
            "--exclude",
            nargs="+",
            type=int,
            default=[],
            help=(
                "A list of item IDs to exclude. Should be integer types. Can be"
                " multiple (view examples page)."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help=(
                "The amount of items to include in the output. Above 100 may be hard to"
                " process, above 150 may be impossible to send. Should be an integer"
                " type. Defaults to 100."
            ),
        )
        parser.add_argument(
            "--file",
            action="store_true",
            help=(
                "If given, will send the full list as an attached .log file, after"
                " exclusion but before limiting."
            ),
        )
        parser.add_argument(
            "--copy",
            "-cc",
            action="store_true",
            help=(
                "If given, will make it easier to copy, without the need to add the"
                " backticks manually."
            ),
        )

        valid_types = [
            "Sword",
            "Shield",
            "Axe",
            "Wand",
            "Dagger",
            "Knife",
            "Spear",
            "Bow",
            "Hammer",
            "Scythe",
            "Howlet",
        ]
        valid_hands = ["left", "right", "any", "both"]

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            return await ctx.send(str(e))

        if args.help:
            chunker = chunks(parser.__dict__["_actions"], 5)
            extras = []
            for big_chunkus in chunker:
                embed = discord.Embed(
                    title="xmerch help",
                    description=(
                        "Here you will find an explanation of all arguments that the"
                        " command can take."
                    ),
                    color=discord.Color.blurple(),
                )
                for small_chunkus in big_chunkus:
                    embed.add_field(
                        name=", ".join(small_chunkus.option_strings),
                        value=small_chunkus.help,
                        inline=False,
                    )
                extras.append(embed)
            expl_embed = discord.Embed(
                title="xmerch help - Examples",
                description="Some examples to familiarize you with the system.",
                color=discord.Color.blurple(),
            )
            expl_embed.add_field(
                name="Getting Scythes and Hammers",
                value="`< xmerch --types Scythe Hammer`",
                inline=False,
            )
            expl_embed.add_field(
                name="Getting right, left and any handed",
                value="`< xmerch --hand right left any`",
                inline=False,
            )
            expl_embed.add_field(
                name="Getting all items expect 123 and 543",
                value="`< xmerch --exclude 123 543`",
                inline=False,
            )
            expl_embed.add_field(
                name="Getting all items from 20 to 5 stat.",
                value="`< xmerch -hi 20 -lo 5`",
                inline=False,
            )
            expl_embed.add_field(
                name=(
                    "Getting xyz#1234's two handed items below 80 damage, above 200"
                    " value, as a file output"
                ),
                value=(
                    "`< xmerch --user @xyz#1234 --hand both -hi 80 -vl 199 --file`\nNote that"
                    " xyz does not have to be member of your server, you can always use"
                    " their User ID."
                ),
                inline=False,
            )
            extras.append(expl_embed)
            pag = Paginator(extras=extras)
            return await pag.paginate(ctx)

        if args.user:
            try:
                conv = commands.MemberConverter()
                user = await conv.convert(ctx, args.user)
                user = user.id
            except commands.CommandError:
                try:
                    user = int(args.user)
                except ValueError:
                    return await ctx.send(
                        f"`--user {args.user}` could not be converted to `discord.User`"
                        " or `int`."
                    )
        else:
            user = ctx.author.id

        upper = abs(args.upper)
        lower = abs(args.lower)

        types = args.type
        for i in types:
            if i not in valid_types:
                types.remove(i)

        hands = args.hand
        for h in hands:
            if h not in valid_hands:
                hands.remove(h)

        lowervalue = abs(args.valuelower)
        uppervalue = abs(args.valueupper)
        hiid = abs(args.idupper)
        loid = abs(args.idlower)

        urls = self.format_url(
            user=user,
            stat_upper=upper or None,
            stat_lower=lower or None,
            types=types or None,
            hands=hands or None,
            value_lower=lowervalue or None,
            value_upper=uppervalue or None,
            id_upper=hiid or None,
            id_lower=loid or None,
        )

        async with ctx.typing():
            itemlist = []
            for query in urls:
                await self.bot.check_for_error_500()
                async with self.bot.session.get(
                    query, headers={"Authorization": self.bot.config.api_token}
                ) as r:
                    status = r.status
                    if status != 200:
                        if int(status / 100) == 5:
                            await self.bot.redis.execute(
                                "SET", f"travapi:520", "timeout", "EX", 3600
                            )
                            return await ctx.send(
                                "The API returned a 5XX error code. This means it is currently not available."
                                " Please try again in one hour."
                            )
                        elif status == 429:
                            return await ctx.send(
                                "429: Ratelimits apply, please try again in a few"
                                " seconds."
                            )
                    res = await r.json()

                itemlist += res

        if len(itemlist) == 0:
            return await ctx.send("No items to merch!")

        itemlist = [str(item["id"]) for item in itemlist if item["inventory"]]
        exc = (
            await self.bot.pool.fetchval(
                'SELECT protected FROM items WHERE "user"=$1', ctx.author.id
            )
            or []
        )
        exc = [str(i) for i in exc]
        exclude = [
            str(i) for i in set(args.exclude)
        ] + exc  # removes dupes too, I'm a genius
        for i in exclude:
            try:
                itemlist.remove(i)
            except ValueError:
                pass

        if len(itemlist) == 0:
            return await ctx.send("No items to merch!")

        if args.file:
            File = discord.File(
                fp=BytesIO(" ".join(itemlist).encode()), filename="items.txt"
            )
            if not ctx.me.permissions_in(ctx.channel).attach_files:
                return await ctx.send("I don't have permission to attach files here :(")
            return await ctx.send(
                "Here is your list!\nPlease note that due to API limitations, this list might be incomplete.",
                file=File,
            )

        limit = abs(args.limit)

        if args.copy:
            output = "\`\`\`\n$merch {0}\n\`\`\`".format(" ".join(itemlist[:limit]))
        else:
            output = "```$merch {0}```".format(" ".join(itemlist[:limit]))
        if len(output) > 2000:
            return await ctx.send(
                "Too many items; message could not be sent! Try setting a lower"
                " `--limit`"
            )
        out = await ctx.send(output)
        if len(itemlist) > limit:
            await ctx.send(
                "This is not the complete list, but rather a shortened one to allow"
                " processing the command.",
                delete_after=10,
            )

        await out.add_reaction("\U0001F5D1")

        def recheck(r, u):
            return (
                str(r.emoji) == "\U0001F5D1"
                and r.message.id == out.id
                and u.id == ctx.author.id
                and not u.bot
            )

        try:
            await self.bot.wait_for("reaction_add", check=recheck, timeout=30)
            return await out.delete()
        except asyncio.TimeoutError:
            try:
                return await out.clear_reactions()
            except discord.Forbidden:
                await out.remove_reaction("\U0001F5D1", ctx.me)


def setup(bot):
    bot.add_cog(Merch(bot))
