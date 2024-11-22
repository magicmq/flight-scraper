import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

APP_HOME = Path(os.getenv('APP_HOME')).resolve()
PASSRIDER_LOGIN = os.getenv('PASSRIDER_LOGIN')
API_URL = os.getenv('API_URL')
FSR_RESULT_URL = os.getenv('FSR_RESULT_URL')
PRL_RESULT_URL = os.getenv('PRL_RESULT_URL')
ERES_USERNAME = os.getenv('ERES_USERNAME')
ERES_PASSWORD = os.getenv('ERES_PASSWORD')
MYSQL_IP = os.getenv('MYSQL_IP')
MYSQL_PORT = os.getenv('MYSQL_PORT')
MYSQL_USERNAME = os.getenv('MYSQL_USERNAME')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_TABLE = os.getenv('MYSQL_TABLE')
MYSQL_TABLE_POST = os.getenv('MYSQL_TABLE_POST')
PUSHOVER_USER = os.getenv('PUSHOVER_USER')
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN')