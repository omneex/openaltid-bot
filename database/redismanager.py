import os
from loguru import logger as log

import redis




def get_redis():
    host = os.environ.get("REDIS_HOST")
    port = os.environ.get("REDIS_PORT")
    password = os.environ.get("REDIS_PASSWORD")

    if host is None or port is None:
        log.critical("Redis Host or Port not supplied.")

    if password is None:
        log.info("No redis password, disabling password auth.")
        redisClient = redis.Redis(host=host, port=port, decode_responses=True)
    else:
        redisClient = redis.Redis(host=host, port=port, password=password, decode_responses=True)
    return redisClient
