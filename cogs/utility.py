import discord
import humanize
from discord.ext import commands

from utils.paginator import Paginator


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} is running")

    @commands.command(alises=["user", "userinfo"])
    async def info(self, ctx, user: discord.Member = None):
        user = user or ctx.author

        baseinfo_embed = discord.Embed(
            title=user.display_name,
            description=str(user),
            color=discord.Color.blurple(),
        )

        baseinfo_embed.set_thumbnail(url=user.avatar_url)
        baseinfo_embed.add_field(name="User ID", value=user.id, inline=False)

        if user.bot:
            baseinfo_embed.add_field(name="This User is a Bot!", value="\u200b")

        baseinfo_embed.add_field(
            name="Joined server at",
            value=humanize.naturaldate(user.joined_at),
            inline=False,
        )
        baseinfo_embed.add_field(
            name="Created at", value=humanize.naturaldate(user.created_at), inline=False
        )

        if user.premium_since:
            baseinfo_embed.add_field(
                name="Boosting server since", value=user.premium_since, inline=False
            )

        if str(user.status) == "online":
            baseinfo_embed.add_field(
                name="Online on...",
                value="Mobile" if user.is_on_mobile() else "PC",
                inline=False,
            )
        else:
            baseinfo_embed.add_field(name="Status", value=str(user.status).title())

        roles_embed = discord.Embed(
            title=f"{user}'s roles",
            description="\n".join([role.name for role in user.roles]),
            color=discord.Color.blurple(),
        )

        newperms = []
        for perm in [x for x in user.guild_permissions]:
            pretty_perm = " ".join(perm[0].split("_")).title()
            if perm[1]:
                newperms.append("\U00002705 {}".format(pretty_perm))
            else:
                newperms.append("\U0000274e {}".format(pretty_perm))

        permissions_embed = discord.Embed(
            title=f"{user}'s permissions in this server",
            description="\n".join(newperms),
            color=discord.Color.blurple(),
        )

        pages = [baseinfo_embed, roles_embed, permissions_embed]
        await Paginator(extras=pages).paginate(ctx)

    @commands.command()
    async def lookup(self, ctx, user_id: int):
        """Look up a user by their ID."""
        if user_id <= 0:
            return await ctx.send(
                "I can already tell you this guy does not exist. "
                "Try using an actual User ID."
            )
        elif len(str(user_id)) == 4:
            return await ctx.send(
                "Did you mistake the User ID for their discriminator? For reference: \n"
                "This is my discrim: `#{discrim}`.\n"
                "This is my User ID: `{id}`".format(
                    discrim=ctx.me.discriminator, id=ctx.me.id
                )
            )

        user = await self.bot.fetch_user(user_id)
        if not user:
            return await ctx.send("Could not find this user.")

        info_embed = discord.Embed(
            title=str(user) + "'s info",
            color=discord.Color.blurple(),
        )

        if user.bot:
            info_embed.add_field(name="This User is a Bot! :robot:", value="\u200b")

        info_embed.set_thumbnail(url=user.avatar_url)
        info_embed.add_field(name="User ID", value=user.id, inline=False)

        info_embed.add_field(
            name="Account created",
            value=humanize.naturaldate(user.created_at),
            inline=False,
        )

        await ctx.send(embed=info_embed)

    @commands.command()
    async def serverinfo(self, ctx):
        server = ctx.guild
        baseinfo = discord.Embed(
            title=server.name,
            description=f"Created by {server.owner}",
            color=discord.Color.blurple(),
        )
        if server.icon_url:
            baseinfo.set_thumbnail(url=server.icon_url)
        else:
            baseinfo.set_thumbnail(url="https://i.imgur.com/YNmPJkh.png")

        baseinfo.add_field(name="Server ID", value=server.id, inline=False)
        baseinfo.add_field(
            name="Server Region", value=str(server.region).title(), inline=False
        )

        members = server.member_count
        bot_count = len([member for member in server.members if member.bot])
        baseinfo.add_field(
            name="Member Count",
            value=f"{members}: {members - bot_count} humans; {bot_count} bots",
            inline=False,
        )

        pages = [baseinfo]

        roles = [role.mention for role in ctx.guild.roles]
        roles.reverse()

        role_chunks = chunks(roles, 15)
        for idx, chunk in enumerate(role_chunks):
            roles = "\n".join(chunk)
            embed = discord.Embed(
                title=f"{ctx.guild.name}'s roles - page {idx+1}",
                description=roles,
                color=discord.Color.blurple(),
            )
            pages.append(embed)

        emoji_chunks = chunks([str(emoji) for emoji in server.emojis], 15)
        for idx, chunk in enumerate(emoji_chunks):
            emojis = "\n".join(
                [f"{emoji} `{discord.utils.escape_markdown(emoji)}`" for emoji in chunk]
            )

            embed = discord.Embed(
                title=f"{ctx.guild.name}'s emojis - page {idx+1}",
                description=emojis,
                color=discord.Color.blurple(),
            )

            embed.timestamp = ctx.message.created_at
            embed.set_footer(text="Pixi")
            pages.append(embed)

        await Paginator(extras=pages).paginate(ctx)

    @commands.command(aliases=["avy", "icon"])
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.send(embed=discord.Embed().set_image(url=user.avatar_url))

    @commands.command(aliases=["perms"])
    async def permissions(
        self, ctx, user: discord.Member = None, channel: discord.TextChannel = None
    ):
        """Get a member's permissions in a channel. If not given, user and channel are the command author and channel respectively"""
        user = user or ctx.author
        channel = channel or ctx.channel

        perms = user.permissions_in(channel)
        newperms = []
        for perm in [x for x in perms]:
            pretty_perm = " ".join(perm[0].split("_")).title()
            if perm[1]:
                newperms.append("\U00002705 {}".format(pretty_perm))
            else:
                newperms.append("\U0000274e {}".format(pretty_perm))

        permissions_embed = discord.Embed(
            title=f"{user}'s permissions in #{channel.name}",
            description="\n".join(newperms),
            color=discord.Color.blurple(),
        )

        await ctx.send(embed=permissions_embed)


def setup(bot):
    bot.add_cog(Utility(bot))
