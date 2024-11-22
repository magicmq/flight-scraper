import os
import requests
from dotenv import load_dotenv

PUSH_URL = 'https://api.pushover.net/1/messages.json'

load_dotenv()
PUSHOVER_USER = os.getenv('PUSHOVER_USER')
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN')

def push_notification(title, message, priority, retry=None, expire=None):
    data = {
        'user': PUSHOVER_USER,
        'token': PUSHOVER_TOKEN,
        'title': title,
        'message': message,
        'priority': priority
    }
    
    if retry is not None:
        data['retry'] = retry

    if expire is not None:
        data['expire'] = expire

    response = requests.post(PUSH_URL, data=data)

    print(response)