import sys
import time
import logging

from flightscraper import search_and_cache
from notify import push_notification

logger = logging.getLogger('flightscraper')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

MAX_TRIES = 3

attempt = 1
while attempt <= MAX_TRIES:
    try:
        search_and_cache(sys.argv[1], sys.argv[2])
        break
    except Exception as e:
        logger.exception(f'Failed to fetch data for flight {sys.argv[1]}-{sys.argv[2]}: {e}.')
        attempt += 1
        if attempt <= MAX_TRIES:
            logger.error(f'Will try again in 5 seconds.')
            time.sleep(5)
        else:
            logger.error(f'Failed to fetch data for flight {sys.argv[1]}-{sys.argv[2]} after {MAX_TRIES} attempts.')
            push_notification(f'Failed to Fetch Flight {sys.argv[1]}-{sys.argv[2]}', f'Failed to fetch data for flight {sys.argv[1]}-{sys.argv[2]}. Aborted after {MAX_TRIES} attempts.\nMost recent error: {e}', 2, retry=60, expire=1800)