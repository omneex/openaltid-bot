from typing import Optional

from loguru import logger as log

from mongoengine.document import Document, EmbeddedDocument
from mongoengine.errors import DoesNotExist, NotUniqueError
from mongoengine.fields import BooleanField, EmbeddedDocumentField, IntField, StringField


class GuildSettings(EmbeddedDocument):
    zero_point = IntField(default=180)
    difficulty_addition = IntField(default=25)
    mfa_bonus = IntField(default=50)
    premium_bonus = IntField(default=11)
    preferred_num_of_accounts = IntField(default=1)


class Guilds(Document):
    meta = {"db_alias": "botdb"}
    guild_ID = StringField(unique=True)
    mod_channel_ID = StringField()
    verification_channel_ID = StringField()
    verification_role_ID = StringField()
    mod_role_ID = StringField()
    prefix_string = StringField(default="$")
    verification_age = IntField(default=90)
    enabled = BooleanField(default=False)
    verify_on_screening = BooleanField(default=True)
    verification_logs_channel_ID = StringField(default="0")
    guild_settings = EmbeddedDocumentField(GuildSettings, default=GuildSettings())


class socialmediaaccounts(Document):
    account_type = StringField()
    account_ID = StringField()
    discord_ID = StringField()

    meta = {"db_alias": "verification_data"}


async def set_verify_on_screening(guild_ID, enabled: bool):
    try:
        guild = Guilds.objects.get(guild_ID=guild_ID)
        guild.verify_on_screening = enabled
        guild.save()
        return None
    except Exception as e:
        log.error(f"Could not set verify_on_screening in guild [{guild_ID}] {e}")
        return e


async def set_guild_mod_role(guild_ID, role_ID):
    try:
        guild = Guilds.objects.get(guild_ID=guild_ID)
        guild.mod_role_ID = role_ID
        guild.save()
        return None
    except Exception as e:
        log.error(f"Could not add role [{role_ID}] to guild [{guild_ID}] {e}")
        return e


async def set_guild_log_channel(guild_ID: str, channel_id: str):
    try:
        guild = Guilds.objects.get(guild_ID=guild_ID)
        guild.verification_logs_channel_ID = int(channel_id)
        guild.save()
        return None
    except Exception as e:
        log.error(f"Could not add log channel [{channel_id}] to guild [{guild_ID}] {e}")
        return e


async def set_guild_enabled(guild_ID, enabled):
    try:
        guild = Guilds.objects.get(guild_ID=guild_ID)
        guild.enabled = enabled
        guild.save()
        return None
    except Exception as e:
        log.error(f"Could not set enabled [{enabled}] to guild [{guild_ID}] {e}")
        return e


async def set_guild_verification_age(guild_ID, age) -> None:
    try:
        guild = Guilds.objects.get(guild_ID=guild_ID)
        guild.verification_age = int(age)
        guild.save()
        return None
    except Exception as e:
        log.error(f"Could not set age to [{age}] to guild [{guild_ID}]")
        return e


async def get_guild_info(guild_ID) -> Optional[Guilds]:
    try:
        guild = Guilds.objects.get(guild_ID=str(guild_ID))
        return guild
    except Exception as e:
        log.error(f"Error while retrieving guild: {e}\n")
        return None


async def insert_verification_data(member_id: str, account_type: str, account_id: str):
    try:
        socialmediaaccounts.objects.get(account_type=account_type, account_ID=account_id)
        return 'Alt found.'
    except DoesNotExist:
        new_entry = socialmediaaccounts(account_type=account_type, account_ID=account_id, discord_ID=member_id)
        new_entry.save()
        return True
    except Exception as e:
        log.error(e)


async def insert_guild(guild_ID):
    try:
        new_guild = Guilds(guild_ID=str(guild_ID))
        new_guild.save()
        return True
    except NotUniqueError:
        log.debug("Guild already exists!")
        return True
    except Exception as e:
        log.error(f"Error occured while inserting guild: {e}")
        return False
