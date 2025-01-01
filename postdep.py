import requests
import time
from datetime import datetime
from datetime import timedelta
from sqlalchemy import create_engine, Table, MetaData
import encode
from collections import Counter
import json
import sys
import logging

from notify import push_notification

from settings import LOGGING_LEVEL, MYSQL_USERNAME, MYSQL_PASSWORD, MYSQL_IP, MYSQL_PORT, MYSQL_TABLE_POST

MAX_TRIES = 3
URL = 'https://www.united.com/en/us/flightstatus/details/{flight_no}/{date}/{origin}/{destination}/UA'
ANON_TOKEN_URL = 'https://www.united.com/api/auth/anonymous-token'
UPGRADE_LIST_URL = 'https://www.united.com/api/flight/upgradeListExtended?flightNumber={flight_no}&flightDate={date}&fromAirportCode={origin}'
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'

logger = logging.getLogger('flightscraper')
logger.setLevel(LOGGING_LEVEL)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

engine = create_engine(f'mysql+mysqldb://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_IP}:{MYSQL_PORT}/data')
data_table = Table(MYSQL_TABLE_POST, MetaData(), autoload_with=engine)
connection = engine.connect()

def fetch(flight_no, date, origin, destination):
    session_url = URL.format(flight_no=flight_no, date=date, origin=origin, destination=destination)

    logger.debug(f'Constructed session URL: {session_url}')

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

    logger.debug(f'Fetched anonymous bearer token: {bearer_token}')

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

    logger.debug('Sending request...')

    response = requests.get(
        UPGRADE_LIST_URL.format(flight_no=flight_no, date=date, origin=origin),
        headers=headers,
        timeout=5
    )

    logger.debug('Request sent.')

    return response.json()

def process(data):
    logger.debug('Processing data...')

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
    front_standby_counts_nci = Counter(item['clearanceType'] for item in data['front']['standby'] if not item['isCheckedIn'])

    middle_cleared_counts = Counter(item['clearanceType'] for item in data['middle']['cleared'])
    middle_standby_counts = Counter(item['clearanceType'] for item in data['middle']['standby'])
    middle_standby_counts_nci = Counter(item['clearanceType'] for item in data['middle']['standby'] if not item['isCheckedIn'])

    rear_cleared_counts = Counter(item['clearanceType'] for item in data['rear']['cleared'])
    rear_standby_counts = Counter(item['clearanceType'] for item in data['rear']['standby'])
    rear_standby_counts_nci = Counter(item['clearanceType'] for item in data['rear']['standby'] if not item['isCheckedIn'])

    timestamp = int(time.time())
    flight_no = str(segment['flightNumber']).zfill(4)
    origin = segment['departureAirportCode']
    destination = segment['arrivalAirportCode']
    date = datetime.strptime(segment['flightDate'], '%Y%m%d')
    day_of_week = date.weekday()
    actual_flight_time = datetime.strptime(segment['scheduledDepartureTime'], '%Y%m%d %I:%M %p').strftime('%I:%M%p').lower().lstrip('0')[:-1]
    hash = encode.encode(flight_no, date.strftime('%m/%d/%Y'), origin, destination)

    logger.debug('Data processed.')
    logger.debug('Inserting data into table...')

    insert_statement = data_table.insert().values(
        hash=hash,
        p_data_timestamp= timestamp,
        flight_no=flight_no,
        origin=origin,
        destination=destination,
        date=date.strftime('%Y-%m-%d'),
        day_of_week=day_of_week,
        actual_flight_time=actual_flight_time,
        p_ca_bu=pbt_front['capacity'],
        p_ca_co=pbt_rear['capacity'],
        p_ca_pp=pbt_middle['capacity'],
        p_ca_to=int(pbt_front['capacity']) + int(pbt_rear['capacity']) + int(pbt_middle['capacity']),
        p_au_bu=pbt_front['authorized'],
        p_au_co=pbt_rear['authorized'],
        p_au_pp=pbt_middle['authorized'],
        p_au_to=int(pbt_front['authorized']) + int(pbt_rear['authorized']) + int(pbt_middle['authorized']),
        p_bo_bu=pbt_front['booked'],
        p_bo_co=pbt_rear['booked'],
        p_bo_pp=pbt_middle['booked'],
        p_bo_to=int(pbt_front['booked']) + int(pbt_rear['booked']) + int(pbt_middle['booked']),
        p_ps_bu=pbt_front['ps'],
        p_ps_co=pbt_rear['ps'],
        p_ps_pp=pbt_middle['ps'],
        p_ps_to=int(pbt_front['ps']) + int(pbt_rear['ps']) + int(pbt_middle['ps']),
        p_sa_bu=pbt_front['sa'],
        p_sa_co=pbt_rear['sa'],
        p_sa_pp=pbt_middle['sa'],
        p_sa_to=int(pbt_front['sa']) + int(pbt_rear['sa']) + int(pbt_middle['sa']),
        p_he_bu=pbt_front['held'],
        p_he_co=pbt_rear['held'],
        p_he_pp=pbt_middle['held'],
        p_he_to=int(pbt_front['held']) + int(pbt_rear['held']) + int(pbt_middle['held']),
        p_gr_bu=pbt_front['group'],
        p_gr_co=pbt_rear['group'],
        p_gr_pp=pbt_middle['group'],
        p_gr_to=int(pbt_front['group']) + int(pbt_rear['group']) + int(pbt_middle['group']),
        p_re_bu=pbt_front['revenueStandby'],
        p_re_co=pbt_rear['revenueStandby'],
        p_re_pp=pbt_middle['revenueStandby'],
        p_re_to=int(pbt_front['revenueStandby']) + int(pbt_rear['revenueStandby']) + int(pbt_middle['revenueStandby']),
        p_ci_bu=check_in_front['total'],
        p_ci_co=check_in_rear['total'],
        p_ci_pp=check_in_middle['total'],
        p_ci_to=int(check_in_front['total']) + int(check_in_rear['total']) + int(check_in_middle['total']),
        p_cl_ug_bu=front_cleared_counts.get('Upgrade', 0),
        p_cl_ug_co=rear_cleared_counts.get('Upgrade', 0),
        p_cl_ug_pp=middle_cleared_counts.get('Upgrade', 0),
        p_cl_sa_bu=front_cleared_counts.get('Standby', 0),
        p_cl_sa_co=rear_cleared_counts.get('Standby', 0),
        p_cl_sa_pp=middle_cleared_counts.get('Standby', 0),
        p_cl_to_bu=sum(front_cleared_counts.values()),
        p_cl_to_co=sum(rear_cleared_counts.values()),
        p_cl_to_pp=sum(middle_cleared_counts.values()),
        p_sy_ug_bu=front_standby_counts.get('Upgrade', 0),
        p_sy_ug_co=rear_standby_counts.get('Upgrade', 0),
        p_sy_ug_pp=middle_standby_counts.get('Upgrade', 0),
        p_sy_sa_bu=front_standby_counts.get('Standby', 0),
        p_sy_sa_co=rear_standby_counts.get('Standby', 0),
        p_sy_sa_pp=middle_standby_counts.get('Standby', 0),
        p_sy_to_bu=sum(front_standby_counts.values()),
        p_sy_to_co=sum(rear_standby_counts.values()),
        p_sy_to_pp=sum(middle_standby_counts.values()),
        p_sy_ug_bu_nci=front_standby_counts_nci.get('Upgrade', 0),
        p_sy_ug_co_nci=rear_standby_counts_nci.get('Upgrade', 0),
        p_sy_ug_pp_nci=middle_standby_counts_nci.get('Upgrade', 0),
        p_sy_sa_bu_nci=front_standby_counts_nci.get('Standby', 0),
        p_sy_sa_co_nci=rear_standby_counts_nci.get('Standby', 0),
        p_sy_sa_pp_nci=middle_standby_counts_nci.get('Standby', 0),
        p_sy_to_bu_nci=front_standby_counts_nci.values(),
        p_sy_to_co_nci=rear_standby_counts_nci.values(),
        p_sy_to_pp_nci=middle_standby_counts_nci.values(),
        p_data_raw=json.dumps(data)
    )
    
    result = connection.execute(insert_statement)
    logger.debug(f'Inserted row into table with ID {result.inserted_primary_key}.')
    logger.debug('Committing connection...')
    connection.commit()
    logger.debug('Connection committed.')

    logger.info(f'Fetched and added flight UAL{flight_no} {origin}-{destination} which departed {date.strftime('%Y-%m-%d')} at {actual_flight_time} to database.')

flights = [
    ('7', 'IAH', 'NRT'),
    ('32', 'LAX', 'NRT'),
    ('837', 'SFO', 'NRT'),
    ('143', 'DEN', 'NRT'),
    ('881', 'ORD', 'HND'),
    ('39', 'LAX', 'HND'),
    ('131', 'EWR', 'HND'),
    ('875', 'SFO', 'HND'),
    ('803', 'IAD', 'HND'),
    ('79', 'EWR', 'NRT'),
    ('35', 'SFO', 'KIX')
]
yesterday = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')

for flight in flights:
    data = None
    attempt = 1

    while attempt <= MAX_TRIES:
        try:
            logger.debug(f'Fetching data for flight {flight[1]}-{flight[2]} on date {yesterday}.')
            data = fetch(flight[0], yesterday, flight[1], flight[2])
            break
        except Exception as e:
            attempt += 1
            logger.error(f'Failed to fetch post-departure data for flight {flight[1]}-{flight[2]}: {e}.')
            if attempt <= MAX_TRIES:
                logger.error(f'Will try again in 5 seconds.')
                time.sleep(5)
            else:
                logger.error(f'Failed to fetch post-departure data for flight {flight[1]}-{flight[2]} after {MAX_TRIES} attempts.')
                push_notification(f'Failed To Fetch Flight {flight[1]}-{flight[2]} (Post-Dep)', f'Failed to fetch post-departure data for flight {flight[1]}-{flight[2]}. Aborted after {MAX_TRIES} attempts.\nMost recent error: {e}', 2, retry=60, expire=1800)

    if data is None:
        time.sleep(15)
        continue
    else: 
        process(data)
        time.sleep(15)

connection.close()

logger.info(f'Finished fetching all flights to NRT/HND on {yesterday}.')
push_notification('Fetched Flights (Post-Departure)', f'Finished fetching all flights to NRT/HND/KIX on {yesterday}.', 0)