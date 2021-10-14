import discord
from database.mongomanager import Guilds


async def is_mod(ctx):
    guild: discord.Guild = ctx.guild
    guild_info = Guilds.objects.get(guild_ID=str(guild.id))
    if guild_info.mod_role_ID is None:
        return ctx.author.guild_permissions.administrator

    return ctx.author.id == int(guild_info.mod_role_ID) or ctx.author.guild_permissions.administrator


async def is_admin(ctx):
    return ctx.author.guild_permissions.administrator
