import discord
from discord.ext import commands
from cogs.checks import is_mod, is_admin
from loguru import logger as log

from database.mongomanager import Guilds


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, name="setvrole")
    @commands.check(is_mod)
    async def set_verification_role(self, ctx, role: int):
        """Set the verification role ID"""
        guild: discord.Guild = ctx.guild
        role: discord.Role = ctx.guild.get_role(role)

        if role is None:
            await ctx.send("That role does not exist.")
            return

        try:
            guild = Guilds.objects.get(guild_ID=str(guild.id))
            guild.verification_role_ID = str(role.id)
            guild.save()
        except Exception as e:
            error = e

        if error is None:
            await ctx.send(f"Verification role set to `{role.name}`")
        else:
            log.error(
                f"Error while adding the role [{role.id}] in guild [{ctx.guild}]. {error}"
            )
            await ctx.send("Internal error while setting the role.")

    @commands.command(pass_context=True, name="setlogs")
    @commands.check(is_mod)
    async def set_logs(self, ctx, channel_id: int):
        """Set the verification channel, use 0 to disable"""
        if channel_id == 0:
            channel_id = "0"
        else:
            log_channel: discord.TextChannel = ctx.guild.get_channel(channel_id)

            if log_channel is None:
                await ctx.send("That channel does not exist.")
                return
            if log_channel.type is not discord.ChannelType.text:
                await ctx.send("That is not a text channel.")

            channel_id = str(log_channel.id)

        try:
            guild: discord.Guild = ctx.guild
            guild = Guilds.objects.get(guild_ID=str(guild.id))
            guild.verification_logs_channel_ID = channel_id
            guild.save()
        except Exception as e:
            error = e

        if error is None:
            if channel_id == "0":
                await ctx.send("Logs have been disabled.")
            else:
                await ctx.send(f"Logs channel set to `{log_channel.name}`")
        else:
            log.error(
                f"Error while adding the role [{log_channel.id}] in guild [{ctx.guild}]. {error}"
            )
            await ctx.send("Internal error while setting the role.")

    @commands.command(pass_context=True, name="setmrole")
    @commands.check(is_admin)
    async def set_mod_role(self, ctx, role: int):
        """Set the mod role ID"""
        role: discord.Role = ctx.guild.get_role(role)
        if role is None:
            await ctx.send("That role does not exist.")
            return
        try:
            guild: discord.Guild = ctx.guild
            guild = Guilds.objects.get(guild_ID=str(guild.id))
            guild.mod_role_ID = str(role.id)
            guild.save()
        except Exception as e:
            error = e

        if error is None:
            await ctx.send(f"Mod role set to `{role.name}`")
        else:
            log.error(
                f"Error while adding the role [{role.id}] in guild [{ctx.guild}]. {error}"
            )
            await ctx.send("Internal error while setting the role.")

    @commands.command(pass_context=True, name="setvage")
    @commands.check(is_mod)
    async def set_verification_age(self, ctx, age: int):
        """Min account age in days"""
        guild: discord.Guild = ctx.guild
        try:
            guild = Guilds.objects.get(guild_ID=str(guild.id))
            guild.verification_age = int(age)
            guild.save()
        except Exception as e:
            error = e

        if error is None:
            await ctx.send(f"Set the min age for verification to {age} days.")
        else:
            log.error(f"{error}")
            await ctx.send("Internal error while setting the age.")

    @commands.command(pass_context=True, name="setenabled")
    @commands.check(is_mod)
    async def set_enabled(self, ctx, enabled: bool):
        """Min account age in days"""
        guild: discord.Guild = ctx.guild
        try:
            guild = Guilds.objects.get(guild_ID=str(guild.id))
            guild.enabled = enabled
            guild.save()
        except Exception as e:
            error = e

        if error is None:
            await ctx.send(f"Set enabled to: {enabled}")
        else:
            log.error(f"{error}")
            await ctx.send("Internal error while setting the age.")
