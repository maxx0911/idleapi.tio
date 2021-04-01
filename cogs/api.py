import asyncio
from io import BytesIO
from pprint import pformat, pprint
from typing import Union
from urllib.parse import unquote

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from config import api_cooldown
from utils.checks import *
from utils.paginator import Paginator


def elongate(string: str, length: int):
    done = f"{string}{' ' * (length - len(string))}"
    return done


class Api(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://public-api.travitia.xyz/idle/"
        self.endpoints = [
            "allitems",
            "children",
            "guild",
            "helpme",
            "inventory",
            "loot",
            "market",
            "pets",
            "profile",
            "server",
            "transactions",
            "user_settings",
        ]
        self.xp_table = {
            1: 0,
            2: 1500,
            3: 9000,
            4: 22500,
            5: 42000,
            6: 67500,
            7: 99000,
            8: 136500,
            9: 180000,
            10: 229500,
            11: 285000,
            12: 346500,
            13: 414000,
            14: 487500,
            15: 567000,
            16: 697410,
            17: 857814,
            18: 1055112,
            19: 1297787,
            20: 1596278,
            21: 1931497,
            22: 2298481,
            23: 2689223,
            24: 3092606,
            25: 3494645,
            26: 3879056,
            27: 4228171,
            28: 4608707,
            29: 5023490,
            30: 5475604,
        }

    def get_level(self, xp) -> int:
        for level, point in self.xp_table.items():
            if xp == point:
                return level
            elif xp < point:
                return level - 1
        return 30

    @commands.cooldown(1, api_cooldown, BucketType.user)
    @commands.command()
    async def get(self, ctx, *, query: str):
        """
        Get data from the API with a query, returned in JSON format.
        If the output is too long, it will be put in an attached txt file.

        The "https://public-api.travitia.xyz/idle/" part of the URL does not need to be included.
        """
        if (
            not query.startswith(self.base_url)
            and not query.split("?")[0] in self.endpoints
        ):
            return await ctx.send(
                "Invalid query! Please make sure your URL starts with"
                " `https://public-api.travitia.xyz/idle/` and it includes a valid"
                " endpoint:\n\n`{0}`".format(", ".join(self.endpoints))
            )
        query = (
            self.base_url + query
            if not query.startswith(self.base_url)
            else query
        )
        color = 0x00FF00
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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
                color = 0xFF0000
            res = await r.json()

        if len(str(res)) > 1500:
            File = discord.File(
                filename="result.txt", fp=BytesIO(pformat(res).encode())
            )
            nres = (
                "{0} entries found, content too long to display. Try paginating"
                " (&limit=10&offset=5), reducing the page size when paginating, or"
                " selecting fewer columns. The full result is attached.".format(
                    len(res)
                )
            )
        else:
            File = None
            nres = pformat(await r.json()).replace(
                "`", "\u200b`\u200b"
            )  # inaccurate, but doesn't break the codeblock in display
        embed = discord.Embed(
            title=str(status),
            description="{0}\n```py\n{1}\n```".format(query, nres),
            color=color,
        )
        await ctx.send(embed=embed, file=File)

    @commands.cooldown(1, api_cooldown, BucketType.user)
    @commands.command()
    async def items(self, ctx, user: int = None):
        """
        Get a user's equipped items.
        [user] is a user ID. If not given, the author's ID is used.
        """
        user = user or ctx.author.id
        person = await self.bot.fetch_user(user)
        query = f"{self.base_url}allitems?select=id,damage,armor,name,type,inventory(equipped)d&owner=eq.{user}&inventory.equipped=is.true"
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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()
            if not res:
                res = "This user has no items equipped or does not have a profile!"
            else:
                res = pformat([r for r in res if r["inventory"]])
        embed = discord.Embed(
            title=f"{person}'s equipped items:",
            description="```py\n{0}\n```".format(res),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)

    @commands.cooldown(1, api_cooldown, BucketType.user)
    @commands.command(aliases=["p", "pp", "me"])
    async def profile(
        self, ctx, *, user: Union[discord.User, discord.Member, int] = None
    ):
        user = user or ctx.author
        if isinstance(user, (discord.Member, discord.User)):
            person = str(user)
            user = user.id
        else:
            try:
                person = await self.bot.fetch_user(user)
            except discord.NotFound:
                return await ctx.send("This user does not exist.")
        query = f"{self.base_url}profile?user=eq.{user}"
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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()
            if not res:
                ponse = "This user has no profile!"
            else:
                dic = res[0]
                max_len = 0
                for item in dic.keys():
                    if len(str(item) + ":") > max_len:
                        max_len = len(str(item))
                ponse = "\n".join(
                    [
                        f"{elongate(x[0]+':', max_len)} {x[1]}"
                        for x in dic.items()
                    ]
                )

            embed = discord.Embed(
                title=f"{person}'s profile",
                description=f"""\
```
{ponse}
```
""",
            )
            await ctx.send(embed=embed)

    @commands.cooldown(1, api_cooldown, BucketType.user)
    @commands.command()
    async def merge(self, ctx, item: Union[int, str]):
        """Finds an item that would be ideal to merge, based on the given item ID or type.

        Equipped items, as well as items with a signature are automatically filtered out."""

        if isinstance(item, int):
            query = f"{self.base_url}allitems?select=*,inventory(equipped)&id=eq.{item}"

        else:
            valid_types = {
                "Sword": "any",
                "Shield": "left",
                "Axe": "any",
                "Wand": "right",
                "Dagger": "any",
                "Knife": "any",
                "Spear": "right",
                "Bow": "both",
                "Hammer": "any",
                "Scythe": "both",
                "Howlet": "both",
            }

            item = item.title().strip()
            if item not in valid_types.keys():
                return await ctx.send(f"`{item}` is not a valid item type.")

            max_ = 82 if valid_types[item] == "both" else 41
            doa = "armor" if item == "Shield" else "damage"
            query = (
                f"{self.base_url}allitems?"
                f"select=*,inventory(equipped)&type=eq.{item.title()}&order={doa}.desc&{doa}=lt.{max_}"
                f"&owner=eq.{ctx.author.id}&limit=1"
            )
            # query gets the highest, still mergeable item of that type

        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query,
            headers={"Authorization": self.bot.config.api_token},
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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()
        if not res:
            if isinstance(item, int):
                return await ctx.send(
                    f"Item `{item}` was not found; check if the ID is right"
                )
            return await ctx.send(
                f"Seems you don't have any `{item}`s (or all `{item}`s you have are above max merge stat)"
            )

        res = res[0]

        if (res["hand"] == "both" and res["damage"] >= 82) or (
            res["hand"] in ["left", "right", "any"]
            and res["damage"] + res["armor"] >= 41
        ):
            return await ctx.send(
                "This item is already at max mergeable stat or above."
            )

        item_id = res["id"]
        doa = "armor" if res["type"] == "Shield" else "damage"
        absmax_ = 82 if res["hand"] == "both" else 41

        if res["owner"] != ctx.author.id:
            if not await ctx.confirm(
                "This item does not belong to you, continue anyway?"
            ):
                return await ctx.send("Command cancelled.")
        if res["inventory"][0]["equipped"]:
            if not await ctx.confirm(
                "This item is currently equipped, continue anyway?"
            ):
                return await ctx.send("Command cancelled.")
        query = (
            "{base_url}allitems?select=*,inventory(equipped)&armor=gte."
            "{_min}&armor=lte.{_max}&type=eq.{_type}&inventory.equipped=is.true&order=armor.asc&signature=is.null"
            "&owner=eq.{owner}".format(
                base_url=self.base_url,
                _min=res["armor"] - 5,
                _max=absmax_
                if res["armor"] + 5 >= absmax_
                else res["armor"] + 5,
                _type=res["type"],
                owner=res["owner"],
            )
            if res["type"] == "Shield"
            else "{base_url}allitems?select=*,inventory(equipped)&damage=gte."
            "{_min}&damage=lte.{_max}&type=eq.{_type}&inventory.equipped=is.true&order=damage.asc&signature=is.null"
            "&owner=eq.{owner}".format(
                base_url=self.base_url,
                _min=res["damage"] - 5,
                _max=absmax_
                if res["damage"] + 5 >= absmax_
                else res["damage"] + 5,
                _type=res["type"],
                owner=res["owner"],
            )
        )

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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            nres = await r.json()

        if not nres:
            return await ctx.send("No fitting items found...")

        items = sorted(
            [
                item
                for item in nres
                if not (item["inventory"] or item["id"] == item_id)
            ],
            key=lambda x: x["armor" if res["type"] == "Shield" else "damage"],
        )

        if not items:
            return await ctx.send("No fitting items found...")

        warn = (
            f":warning: The best possible item has a higher {doa} than the original item. Consider switching the IDs around."
            if (
                items[0]["damage"] + items[0]["armor"]
                > res["damage"] + res["armor"]
            )
            else ""
        )

        await ctx.send(
            f"""\
{warn}

Found {len(items)} mergable item(s).

{item_id}: {res["damage"]+res["armor"]} {doa} {res["type"]} + 
{items[0]["id"]}: {items[0]["damage"] + items[0]["armor"]} {doa} {items[0]["type"]}
==========
{item_id}: {res["damage"]+res["armor"] + 1} {doa} {res["type"]}

`$merge {item_id} {items[0]["id"]}`"""
        )

    @commands.cooldown(1, api_cooldown, BucketType.user)
    @commands.command(aliases=["item", "i"])
    async def iteminfo(self, ctx, *itemids: int):
        """Get info on item(s), from their owners to signatures and stats."""
        if not itemids:
            return await ctx.send(
                "Please supply some Item IDs, for example `< item 123 234 345`"
            )
        if len(itemids) > 250:
            await ctx.send(
                ":warning: Cannot view more than 250 items at a time, only selecting the first 250"
            )
            itemids = itemids[0:249]
        joined_items = ",".join(str(i) for i in itemids)
        query = f"{self.base_url}allitems?id=in.({joined_items})"

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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()

        if not res:
            if len(itemids) == 1:
                return await ctx.send(
                    f"""The item with the ID `{itemids[0]}` was not found. This might mean:
    - You mistyped the ID
    - The item does not exist *yet*
    - The item does not exist *anymore* (most likely merched)"""
                )
            else:
                items = ", ".join(str(x) for x in itemids)
                return await ctx.send(
                    f"""No items with the IDs `{items}` were found. This might mean:
    - You mistyped the IDs
    - The items do not exist *yet*
    - The items do not exist *anymore* (most likely merched)"""
                )

        # item = res[0]

        item_embeds = []

        for item in res:

            pn = (
                "An"
                if item["type"].startswith(("A", "E", "I", "O", "U"))
                else "A"
            )
            doa = "armor" if item["type"] == "Shield" else "damage"
            stat = item["damage"] + item["armor"]
            owner = await self.bot.fetch_user(item["owner"])

            embed = discord.Embed(
                title=item["name"],
                description=f"{pn} {item['type'].lower()} with {stat} {doa}",
            )
            # embed.add_thumbnail(url=f"attachment://{item['type']}.png")
            embed.add_field(
                name="Currently owned by",
                value=f"{owner} ({item['owner']})",
                inline=False,
            )
            embed.add_field(
                name="General info",
                value="Item ID: {0}\nItem value: {1}\nHand used: {2}".format(
                    item["id"], item["value"], item["hand"]
                ),
                inline=False,
            )

            if item["signature"]:
                embed.add_field(
                    name="Signature", value=item["signature"], inline=False
                )
            if item["original_type"]:
                pn = (
                    "An"
                    if item["original_type"].startswith(
                        ("A", "E", "I", "O", "U")
                    )
                    else "A"
                )
                embed.add_field(
                    name="Original Type",
                    value=f"This item was originally {pn} {item['original_type']}",
                )
            item_embeds.append(embed)

        await Paginator(extras=item_embeds).paginate(ctx)

        # await ctx.send(embed=embed)

    def get_guild(self, *, name: str = None, _id: int = None) -> str:
        if not name and not _id:
            raise ValueError("Neither name nor ID given")
        if _id:
            url = f"{self.base_url}guild?id=eq.{_id}&limit=1"
        else:
            url = f"{self.base_url}guild?name=eq.{name}"
        return url

    @commands.cooldown(1, api_cooldown, BucketType.user)
    @commands.command(usage="<Name or ID>")
    async def guildmembers(self, ctx, *, name_or_id: Union[int, str]):
        """Returns a list of all guild, paginated"""
        # get the type and get the guild from that
        if type(name_or_id) == str:
            url = self.get_guild(name=name_or_id)
        else:
            url = self.get_guild(_id=name_or_id)

        async with self.bot.session.get(
            url, headers={"Authorization": self.bot.config.api_token}
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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()

        # this is a guild
        if not res:
            helpful = (
                "Please make sure that capitalization and spelling of the guild name is correct, or use its ID."
                if type(name_or_id) == str
                else "Please make sure the ID is correct."
            )
            return await ctx.send(f"Guild `{name_or_id}` not found. {helpful}")

        # now we actually have a guild
        # we get the members by its ID
        guild_id = res[0]["id"]
        url = f"{self.base_url}profile?guild=eq.{guild_id}"
        async with self.bot.session.get(
            url, headers={"Authorization": self.bot.config.api_token}
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
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()

        # now we have a list of members
        if not res:
            return await ctx.send(
                "Somehow this guild does not have any members. I have no idea how this happened."
            )

        if await ctx.confirm(
            "Do you wanna get the usernames too? Might take a while."
        ):
            GET_USERNAMES = True
        else:
            GET_USERNAMES = False

        embeds = []

        async with ctx.channel.typing():
            for member in res:
                member["level"] = self.get_level(member["xp"])
                if GET_USERNAMES:
                    member["username"] = ctx.guild.get_member(member["user"])
                    if not member["username"]:
                        member["username"] = await self.bot.fetch_user(
                            member["user"]
                        )
                        # await asyncio.sleep(0.5)
                else:
                    member["username"] = member["user"]

                max_len = 0
                for item in member.keys():
                    if len(str(item) + ":") > max_len:
                        max_len = len(str(item))
                ponse = "\n".join(
                    [
                        f"{elongate(x[0]+':', max_len)} {x[1]}"
                        for x in member.items()
                    ]
                )

                embed = discord.Embed(
                    title=str(member["username"]),
                    description=f"""\
```
{ponse}
```
""",
                )
                embeds.append(embed)

        await Paginator(extras=embeds).paginate(ctx)


def setup(bot):
    bot.add_cog(Api(bot))
