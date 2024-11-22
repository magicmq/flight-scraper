import sys
import time
import os
import logging
from pathlib import Path

from dotenv import load_dotenv

from flightscraper import search_and_cache

logger = logging.getLogger('flightscraper')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()
MAX_TRIES = 3
HOME_DIRECTORY = Path(os.getenv('APP_HOME')).resolve()

attempt = 1
while attempt <= MAX_TRIES:
    try:
        search_and_cache(sys.argv[1], sys.argv[2])
        break
    except Exception as e:
        logger.exception(f'Failed to fetch data for flight {sys.argv[1]}-{sys.argv[2]}.')
        attempt += 1
        if attempt <= MAX_TRIES:
            logger.error(f'Will try again in 5 seconds.')
            time.sleep(5)
        else:
            logger.error(f'Failed to fetch data for flight {sys.argv[1]}-{sys.argv[2]} after {MAX_TRIES} attempts.')