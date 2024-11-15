import sys
import subprocess
import time
import os
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [wrapper-%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()
MAX_TRIES = 3
HOME_DIRECTORY = Path(os.getenv('APP_HOME')).resolve()

success = False
attempt = 1
while attempt <= MAX_TRIES:
    result = subprocess.run(['python3', str(HOME_DIRECTORY / Path('flightscraper.py')), sys.argv[1], sys.argv[2]])
    if result.returncode == 1:
        attempt += 1
        logger.error(f'Failed to fetch data for flight {sys.argv[1]}-{sys.argv[2]}.')
        if attempt <= MAX_TRIES:
            logger.error(f'Will try again in 5 seconds.')
            time.sleep(5)
    else:
        success = True
        break

if not success:
    logger.error(f'Failed to fetch flight data for flight {sys.argv[1]}-{sys.argv[2]} after {MAX_TRIES} attempts.')