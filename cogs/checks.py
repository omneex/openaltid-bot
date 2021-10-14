from database.mongomanager import get_guild_info


async def is_mod(ctx):
    guild_info = await get_guild_info(ctx.guild.id)
    if guild_info.mod_role_ID is None:
        return ctx.author.guild_permissions.administrator

    return ctx.author.id == int(guild_info.mod_role_ID) or ctx.author.guild_permissions.administrator


async def is_admin(ctx):
    return ctx.author.guild_permissions.administrator
