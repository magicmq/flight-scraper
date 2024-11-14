from dotenv import load_dotenv
import os
import requests
import time
from datetime import datetime
from datetime import timedelta
import sqlite3
import encode
from collections import Counter
import json
import sys
import logging

URL = 'https://www.united.com/en/us/flightstatus/details/{flight_no}/{date}/{origin}/{destination}/UA'
ANON_TOKEN_URL = 'https://www.united.com/api/auth/anonymous-token'
UPGRADE_LIST_URL = 'https://www.united.com/api/flight/upgradeListExtended?flightNumber={flight_no}&flightDate={date}&fromAirportCode={origin}'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
INSERT_STATEMENT = 'INSERT INTO data_post (`p_data_timestamp`, `hash`, `flight_no`, `origin`, `destination`, `date`, `day_of_week`, `actual_flight_time`, `p_ca_bu`, `p_ca_co`, `p_ca_pp`, `p_ca_to`, `p_au_bu`, `p_au_co`, `p_au_pp`, `p_au_to`, `p_bo_bu`, `p_bo_co`, `p_bo_pp`, `p_bo_to`, `p_ps_bu`, `p_ps_co`, `p_ps_pp`, `p_ps_to`, `p_sa_bu`, `p_sa_co`, `p_sa_pp`, `p_sa_to`, `p_he_bu`, `p_he_co`, `p_he_pp`, `p_he_to`, `p_gr_bu`, `p_gr_co`, `p_gr_pp`, `p_gr_to`, `p_re_bu`, `p_re_co`, `p_re_pp`, `p_re_to`, `p_ci_bu`, `p_ci_co`, `p_ci_pp`, `p_ci_to`, `p_cl_ug_bu`, `p_cl_ug_co`, `p_cl_ug_pp`, `p_cl_sa_bu`, `p_cl_sa_co`, `p_cl_sa_pp`, `p_cl_to_bu`, `p_cl_to_co`, `p_cl_to_pp`, `p_sy_ug_bu`, `p_sy_ug_co`, `p_sy_ug_pp`, `p_sy_sa_bu`, `p_sy_sa_co`, `p_sy_sa_pp`, `p_sy_to_bu`, `p_sy_to_co`, `p_sy_to_pp`, `p_data_raw`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [postdep-%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()
HOME_DIRECTORY = os.getenv('APP_HOME')

database_connection = sqlite3.connect(f'{HOME_DIRECTORY}data.db')
cursor = database_connection.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS `data_post` (
    `id` INTEGER PRIMARY KEY,
    `p_data_timestamp`,
    `hash`,
    `flight_no`,
    `origin`,
    `destination`,
    `date`,
    `day_of_week`,
    `actual_flight_time`,
    `p_ca_bu`,
    `p_ca_co`,
    `p_ca_pp`,
    `p_ca_to`,
    `p_au_bu`,
    `p_au_co`,
    `p_au_pp`,
    `p_au_to`,
    `p_bo_bu`,
    `p_bo_co`,
    `p_bo_pp`,
    `p_bo_to`,
    `p_ps_bu`,
    `p_ps_co`,
    `p_ps_pp`,
    `p_ps_to`,
    `p_sa_bu`,
    `p_sa_co`,
    `p_sa_pp`,
    `p_sa_to`,
    `p_he_bu`,
    `p_he_co`,
    `p_he_pp`,
    `p_he_to`,
    `p_gr_bu`,
    `p_gr_co`,
    `p_gr_pp`,
    `p_gr_to`,
    `p_re_bu`,
    `p_re_co`,
    `p_re_pp`,
    `p_re_to`,
    `p_ci_bu`,
    `p_ci_co`,
    `p_ci_pp`,
    `p_ci_to`,
    `p_cl_ug_bu`,
    `p_cl_ug_co`,
    `p_cl_ug_pp`,
    `p_cl_sa_bu`,
    `p_cl_sa_co`,
    `p_cl_sa_pp`,
    `p_cl_to_bu`,
    `p_cl_to_co`,
    `p_cl_to_pp`,
    `p_sy_ug_bu`,
    `p_sy_ug_co`,
    `p_sy_ug_pp`,
    `p_sy_sa_bu`,
    `p_sy_sa_co`,
    `p_sy_sa_pp`,
    `p_sy_to_bu`,
    `p_sy_to_co`,
    `p_sy_to_pp`,
    `p_data_raw`
)
''')
database_connection.commit()

def fetch(flight_no, date, origin, destination):
    session_url = URL.format(flight_no=flight_no, date=date, origin=origin, destination=destination)

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US',
        'connection': 'keep-alive',
        'dnt': '1',
        'referer': session_url,
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': USER_AGENT,
    }

    response = requests.get('https://www.united.com/api/auth/anonymous-token', headers=headers)

    bearer_token = response.json()['data']['token']['hash']

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'connection': 'keep-alive',
        'referer': session_url,
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': USER_AGENT,
        'x-authorization-api': f'bearer {bearer_token}',
    }

    response = requests.get(
        UPGRADE_LIST_URL.format(flight_no=flight_no, date=date, origin=origin),
        headers=headers,
        timeout=5
    )

    return response.json()

def process(data):
    segment = data['segment']

    pbts = data['pbts']
    pbt_front = pbts[0]
    pbt_middle = pbts[1]
    pbt_rear = pbts[2]

    check_in = data['checkInSummaries']
    check_in_front = check_in[0]
    check_in_middle = check_in[1]
    check_in_rear = check_in[2]

    front_cleared_counts = Counter(item['clearanceType'] for item in data['front']['cleared'])
    front_standby_counts = Counter(item['clearanceType'] for item in data['front']['standby'])

    middle_cleared_counts = Counter(item['clearanceType'] for item in data['middle']['cleared'])
    middle_standby_counts = Counter(item['clearanceType'] for item in data['middle']['standby'])

    rear_cleared_counts = Counter(item['clearanceType'] for item in data['rear']['cleared'])
    rear_standby_counts = Counter(item['clearanceType'] for item in data['rear']['standby'])

    timestamp = int(time.time())
    flight_no = str(segment['flightNumber']).zfill(4)
    origin = segment['departureAirportCode']
    destination = segment['arrivalAirportCode']
    date = datetime.strptime(segment['flightDate'], '%Y%m%d').strftime('%m/%d/%Y')
    day_of_week = datetime.strptime(segment['flightDate'], '%Y%m%d').weekday()
    actual_flight_time = datetime.strptime(segment['scheduledDepartureTime'], '%Y%m%d %I:%M %p').strftime('%I:%M%p').lower().lstrip('0')[:-1]

    cursor.execute(
        INSERT_STATEMENT, 
        (
            timestamp,
            encode.encode(flight_no, date, origin, destination),
            flight_no,
            origin,
            destination,
            date,
            day_of_week,
            actual_flight_time,
            pbt_front['capacity'],
            pbt_rear['capacity'],
            pbt_middle['capacity'],
            int(pbt_front['capacity']) + int(pbt_rear['capacity']) + int(pbt_middle['capacity']),
            pbt_front['authorized'],
            pbt_rear['authorized'],
            pbt_middle['authorized'],
            int(pbt_front['authorized']) + int(pbt_rear['authorized']) + int(pbt_middle['authorized']),
            pbt_front['booked'],
            pbt_rear['booked'],
            pbt_middle['booked'],
            int(pbt_front['booked']) + int(pbt_rear['booked']) + int(pbt_middle['booked']),
            pbt_front['ps'],
            pbt_rear['ps'],
            pbt_middle['ps'],
            int(pbt_front['ps']) + int(pbt_rear['ps']) + int(pbt_middle['ps']),
            pbt_front['sa'],
            pbt_rear['sa'],
            pbt_middle['sa'],
            int(pbt_front['sa']) + int(pbt_rear['sa']) + int(pbt_middle['sa']),
            pbt_front['held'],
            pbt_rear['held'],
            pbt_middle['held'],
            int(pbt_front['held']) + int(pbt_rear['held']) + int(pbt_middle['held']),
            pbt_front['group'],
            pbt_rear['group'],
            pbt_middle['group'],
            int(pbt_front['group']) + int(pbt_rear['group']) + int(pbt_middle['group']),
            pbt_front['revenueStandby'],
            pbt_rear['revenueStandby'],
            pbt_middle['revenueStandby'],
            int(pbt_front['revenueStandby']) + int(pbt_rear['revenueStandby']) + int(pbt_middle['revenueStandby']),
            check_in_front['total'],
            check_in_rear['total'],
            check_in_middle['total'],
            int(check_in_front['total']) + int(check_in_rear['total']) + int(check_in_middle['total']),
            front_cleared_counts.get('Upgrade', 0),
            rear_cleared_counts.get('Upgrade', 0),
            middle_cleared_counts.get('Upgrade', 0),
            front_cleared_counts.get('Standby', 0),
            rear_cleared_counts.get('Standby', 0),
            middle_cleared_counts.get('Standby', 0),
            sum(front_cleared_counts.values()),
            sum(rear_cleared_counts.values()),
            sum(middle_cleared_counts.values()),
            front_standby_counts.get('Upgrade', 0),
            rear_standby_counts.get('Upgrade', 0),
            middle_standby_counts.get('Upgrade', 0),
            front_standby_counts.get('Standby', 0),
            rear_standby_counts.get('Standby', 0),
            middle_standby_counts.get('Standby', 0),
            sum(front_standby_counts.values()),
            sum(rear_standby_counts.values()),
            sum(middle_standby_counts.values()),
            json.dumps(data)
        )
    )
    database_connection.commit()
    logger.info(f'Fetched and added flight UAL{flight_no} {origin}-{destination} which departed {date} at {actual_flight_time} to database.')

flights = [
    ('7', 'IAH', 'NRT'),
    ('32', 'LAX', 'NRT'),
    ('837', 'SFO', 'NRT'),
    ('143', 'DEN', 'NRT'),
    ('881', 'ORD', 'HND'),
    ('39', 'LAX', 'HND'),
    ('131', 'EWR', 'HND'),
    ('875', 'SFO', 'HND'),
    ('803', 'IAD', 'HND')
]
yesterday = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')

for flight in flights:
    data = fetch(flight[0], yesterday, flight[1], flight[2])
    process(data)
    time.sleep(2)

logger.info(f'Finished fetching all flights to NRT/HND on {yesterday}.')