import os

import discord
import mongoengine
from discord.ext import commands
from dotenv import load_dotenv
from loguru import logger as log
from cogs.management_cog import Management
from cogs.verification_cog import Verification
from database.mongomanager import insert_guild, get_guild_info
from database.redismanager import get_redis

load_dotenv()
redisClient = get_redis()

intents = discord.Intents.default()
intents.members = True
bot_token = os.environ.get('BOT_TOKEN')
if bot_token is None:
    log.critical("NO BOT TOKEN SUPPLIED")
    exit(0)

print("VERSION: 1.2")

def connect():
    log.info('Connecting to MongoDB...')
    try:
        db_name = os.environ.get('DB_NAME')
        db_host = os.environ.get('DB_HOST')
        mongoengine.connect("botdb", host=db_host, alias="botdb")
        mongoengine.connect("verification_data", host=db_host, alias="verification_data")
        log.success("Connected to database.")
    except Exception as e:
        log.critical(f"Unable to connect to database! {e}")


async def get_prefix(bot, message):
    try:
        settings = await get_guild_info(message.guild.id)
        return settings.prefix_string
    except Exception as e:
        log.critical(e)
        return "$"


bot = commands.Bot(description="Open/Alt.ID", command_prefix=get_prefix, pm_help=False,
                   intents=intents)


@bot.event
async def on_ready():
    log.info('Logged in as ' + str(bot.user.name) + ' (ID:' + str(bot.user.id) + ') | Connected to '
             + str(len(bot.guilds)) + ' servers | Connected to ' + str(len(set(bot.get_all_members())))
             + ' users')
    log.info("Loading guilds!")

    for guild in bot.guilds:
        log.debug(f"Loading guild '{guild.name}' with ID '{guild.id}'")
        success = await insert_guild(guild.id)
        if not success:
            log.critical(f"Failed to insert {guild.name}")

    log.success("Bot is now ready.")
    return await bot.change_presence(activity=discord.Game('with bits'))


@bot.event
async def on_guild_join(guild):
    log.debug(f"Loading guild '{guild.name}' with ID '{guild.id}'")
    success = await insert_guild(guild.id)
    if not success:
        log.critical(f"Failed to insert {guild.name}")


def run_client():
    while True:
        connect()
        try:
            bot.add_cog(Verification(bot))
            bot.add_cog(Management(bot))
            # bot.add_cog(Music(bot))
        except Exception as e:
            log.critical(f'Error while adding initializing cogs! {e}')

        try:
            bot.run(bot_token)
        finally:
            bot.clear()
            log.warning('The bot is restarting!')


run_client()
