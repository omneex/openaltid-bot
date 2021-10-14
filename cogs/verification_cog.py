import asyncio
import os
import secrets
import time
from asyncio import sleep
from datetime import datetime, timedelta

import discord
from discord import Forbidden
from discord.ext import tasks, commands
from mongoengine.errors import DoesNotExist
import redis
from loguru import logger as log
from redis.exceptions import LockError
from database.mongomanager import SocialMediaAccounts, get_guild_info
from database.redismanager import get_redis

async def initiate_verification(redisClient, member, guild_settings, enabled, bot):
    if not enabled:
        return 'Not Enabled.'
    if guild_settings.verification_role_ID is None:
        log.error("The guild does not have a verification role set!")
        return 'No verification role.'



    mintime = datetime.utcnow() - timedelta(days=guild_settings.verification_age)

    if member.created_at <= mintime:
        # Dont need to verify
        role = member.guild.get_role(int(guild_settings.verification_role_ID))
        try:
            await member.add_roles(role)
            log.debug(f'Verification logs channel: {guild_settings.verification_logs_channel_ID}')
            if guild_settings.verification_logs_channel_ID != 0:
                log.debug("Sending logs to verification channel.")
                channel = bot.get_channel(int(guild_settings.verification_logs_channel_ID))

                embed = discord.Embed(title="Verification Passed!", colour=discord.Colour(0x7ed321), description="The user passed verification.", timestamp=datetime.utcnow())

                embed.set_author(name="Open/Alt.ID Logs", url="https://github.com/omneex/OpenAltID")
                embed.set_footer(text="Powered by Open/Alt.ID")

                embed.add_field(name="User Mention", value=f"<@{member.id}>")
                embed.add_field(name="User ID", value=f"{member.id}")
                embed.add_field(name="Reason", value=f"__Above minimum age, no verification performed.__")

                await channel.send(embed=embed)
            return True
        except Exception as err:
            log.error(err)
            return err

    channel = bot.get_channel(int(guild_settings.verification_logs_channel_ID))

    embed = discord.Embed(title="Verification Initiated!", colour=discord.Colour(0xf0f043), description="Verification link has been sent to the user!", timestamp=datetime.utcnow())

    embed.set_author(name="Open/Alt.ID Logs", url="https://github.com/omneex/OpenAltID")
    embed.set_footer(text="Powered by Open/Alt.ID")

    embed.add_field(name="User Mention", value=f"<@{member.id}>")
    embed.add_field(name="User ID", value=f"{member.id}")

    await channel.send(embed=embed)
    retry = True
    unique_ID = secrets.token_urlsafe(8)
    """
    Keys: uuid:[unique_string]
    Values: [member_id]:[guild_id]
    """
    try:
        while retry:
            if redisClient.get(f"uuid:{unique_ID}") is None:
                redisClient.set(f"uuid:{unique_ID}", f"{member.id}:{member.guild.id}", ex=3600)
                retry = False
            else:
                unique_ID = secrets.token_urlsafe(8)
    except Exception as err:
        log.error(err)
        return "Internal Redis error"

    verify_link = f"{os.environ.get('FRONTEND_HOST')}/verify/{unique_ID}"
    if redisClient.get(f"uuid:{unique_ID}") == f"{member.id}:{member.guild.id}":
        try:
            await member.send(f"Thank you for joining! __You must connect social media accounts to your Discord first__, then go to this link to verify: {verify_link}\n Supported account types: \n- YouTube\n- Twitter\n- Twitch\n- Reddit")
            return True
        except Forbidden:
            return "DMs are not open, please allow DMs and try again."
    else:
        return "Internal Redis error"


class Verification(commands.Cog):
    def __init__(self, bot):
        self.index = 0
        self.bot = bot
        self.check_completed.start()
        self.redisClient = get_redis()
        log.success("Connected to Redis.")

    def cog_unload(self):
        self.check_completed.cancel()

    @commands.command(name="verify")
    async def manual_verify(self, ctx):
        # TODO allow servers to disable message auto deleting
        guild_id = ctx.guild.id
        guild_settings = await get_guild_info(guild_id)
        try:
            # Always enable it here
            queued = await initiate_verification(self.redisClient, ctx.author, guild_settings, True, self.bot)
            if queued is True:
                await ctx.message.add_reaction("✅")
            else:
                bot_msg = await ctx.channel.send(f"Something went wrong: {queued}")
                await bot_msg.delete(delay=20)

            await ctx.message.delete(delay=20)
        except Exception as e:
            bot_msg = await ctx.channel.send(f"An error occured while queuing verification: {e}")
            await bot_msg.delete(delay=20)
            log.error(e)

    @commands.command(name="forceverify")
    async def force_verify(self, ctx, user: discord.Member):
        await ctx.channel.send(
            f"Forced verify for {user.mention} started. Add accounts in the format of '[account type] [account id]' ("
            f"for Reddit use the username).")

        def check(message):
            return (len(message.content.split(' ')) == 2 or message.content.lower() == 'done') and \
                   (message.channel == ctx.channel) and message.author == ctx.author

        def check_yes_no(message):
            return (message.content.lower() == 'yes' or message.content.lower() == 'no') and \
                   (message.channel == ctx.channel) and message.author == ctx.author

        while True:
            msg = await ctx.bot.wait_for('message', check=check, timeout=120)
            if msg.content == 'done':
                await msg.add_reaction('✅')
                break
            else:
                split_msg = msg.content.split(' ')

                account_type = split_msg[0]
                account_id = split_msg[1]
                await ctx.channel.send(
                    f'Account Type:`{account_type}` Account ID:`{account_id}`\n  Confirm: `yes` or `no`?')
                new_msg = await ctx.bot.wait_for('message', check=check_yes_no, timeout=60)
                if new_msg.content == 'yes':
                    try:
                        SocialMediaAccounts.objects.get(account_type=account_type, account_ID=account_id)
                        return 'Alt found.'
                    except DoesNotExist:
                        new_entry = SocialMediaAccounts(account_type=account_type, account_ID=account_id, discord_ID=member_id)
                        new_entry.save()
                        result = True
                    except Exception as e:
                        pass
                    if result is True:
                        await ctx.channel.send(f'Connection added. Add more accounts or type `done` to finish.')
                    else:
                        await ctx.channel.send(f'Failed to add connections: {result}')
                else:
                    await ctx.channel.send(f'Connection was not added. Add more accounts or type `done` to finish.')



    @tasks.loop(seconds=5.0)
    async def check_completed(self):
        key_prefix = "complete"
        '''
            Format for completed verification keys is: complete:{userid}:{guildid}
            Value must be either 'true' or 'false'
            '''
        try:
            for key in self.redisClient.scan_iter(f"{key_prefix}:*"):
                with self.redisClient.lock("lock:" + key, blocking_timeout=5):
                    log.debug(f"Acquired lock for {key}.")
                    value = self.redisClient.get(key)
                    if value.startswith("true"):
                        key_split = key.split(':')
                        user_id = key_split[1]
                        guild_id = key_split[2]

                        value_split = value.split(':')
                        score = value_split[1]
                        minscore = value_split[2]

                        guild = self.bot.get_guild(int(guild_id))
                        member = guild.get_member(int(user_id))

                        guild_settings = await get_guild_info(guild_id)
                        if guild_settings.verification_role_ID is None:
                            log.error("The guild does not have a verification role set!")
                            return
                        role = guild.get_role(int(guild_settings.verification_role_ID))

                        await member.add_roles(role)

                        self.redisClient.delete(key)
                        log.info(f"User: {user_id} was verified in {guild_id}  Score: {score}/{minscore}")
                        if guild_settings.verification_logs_channel_ID != 0:
                            channel = self.bot.get_channel(int(guild_settings.verification_logs_channel_ID))

                            embed = discord.Embed(title="Verification Passed!", colour=discord.Colour(0x7ed321), description="The user passed verification.", timestamp=datetime.utcnow())

                            embed.set_author(name="Open/Alt.ID Logs", url="https://github.com/omneex/OpenAltID")
                            embed.set_footer(text="Powered by Open/Alt.ID")

                            embed.add_field(name="User Mention", value=f"<@{user_id}>")
                            embed.add_field(name="User ID", value=f"{user_id}")
                            embed.add_field(name="Score", value=f"**{score}** / {minscore}")

                            await channel.send(embed=embed)
                    elif value.startswith("error"):
                        key_split = key.split(':')
                        user_id = key_split[1]
                        guild_id = key_split[2]

                        value_split = value.split(':')
                        reason = value_split[1]

                        guild_settings = await get_guild_info(guild_id)
                        if guild_settings.verification_role_ID is None:
                            log.error("The guild does not have a verification role set!")
                            return

                        self.redisClient.delete(key)
                        log.info(f"User: {user_id} was NOT verified in {guild_id} Reason: {reason}")
                        if guild_settings.verification_logs_channel_ID != 0:
                            channel = self.bot.get_channel(int(guild_settings.verification_logs_channel_ID))

                            embed = discord.Embed(title="Verification Failed!", colour=discord.Colour(0xd0021b), description="The user could not be verified.", timestamp=datetime.utcnow())

                            embed.set_author(name="Open/Alt.ID Logs", url="https://github.com/omneex/OpenAltID")
                            embed.set_footer(text="Powered by Open/Alt.ID")

                            embed.add_field(name="User Mention", value=f"<@{user_id}>")
                            embed.add_field(name="User ID", value=f"{user_id}")
                            embed.add_field(name="Reason", value=f"__{reason}__")

                            await channel.send(embed=embed)
                    else:
                        key_split = key.split(':')
                        user_id = key_split[1]
                        guild_id = key_split[2]

                        value_split = value.split(':')
                        score = value_split[1]
                        minscore = value_split[2]

                        guild_settings = await get_guild_info(guild_id)

                        log.debug(guild_settings)

                        if guild_settings.verification_role_ID is None:
                            log.error("The guild does not have a verification role set!")
                            return

                        self.redisClient.delete(key)
                        log.info(f"User: {user_id} was NOT verified in {guild_id} Score: {score}/{minscore}")
                        if guild_settings.verification_logs_channel_ID != 0:
                            channel = self.bot.get_channel(int(guild_settings.verification_logs_channel_ID))

                            embed = discord.Embed(title="Verification Failed!", colour=discord.Colour(0xd0021b), description="The user did not pass verification.", timestamp=datetime.utcnow())

                            embed.set_author(name="Open/Alt.ID Logs", url="https://github.com/omneex/OpenAltID")
                            embed.set_footer(text="Powered by Open/Alt.ID")

                            embed.add_field(name="User Mention", value=f"<@{user_id}>")
                            embed.add_field(name="User ID", value=f"{user_id}")
                            embed.add_field(name="Score", value=f"**{score}** / {minscore}")

                            await channel.send(embed=embed)
        except LockError as e:
            log.exception(f"Did not acquire lock for {key}. {e}")
        except Exception as e:
            log.error(f"Failed to get keys! {e}")

    @check_completed.before_loop
    async def before_printer(self):
        log.info("Verification loop waiting for bot to be ready...")
        await self.bot.wait_until_ready()
