import os
import time
from datetime import datetime
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import sqlite3
import encode
from fetch import fetch

INSERT_STATEMENT = 'INSERT INTO `data` (`id`, `data_timestamp`, `hash`, `flight_no`, `origin`, `destination`, `date`, `day_of_week`, `flight_time`, `av_bu`, `av_co`, `av_pp`, `av_to`, `ca_bu`, `ca_co`, `ca_pp`, `ca_to`, `au_bu`, `au_co`, `au_pp`, `au_to`, `bo_bu`, `bo_co`, `bo_pp`, `bo_to`, `ps_bu`, `ps_co`, `ps_pp`, `ps_to`, `sa_bu`, `sa_co`, `sa_pp`, `sa_to`, `he_bu`, `he_co`, `he_pp`, `he_to`, `gr_bu`, `gr_co`, `gr_pp`, `gr_to`, `re_bu`, `re_co`, `re_pp`, `re_to`, `pos_va`, `pos_pe`, `flight_raw`, `pass_rider_raw`) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [flightscraper-%(name)s] [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()
HOME_DIRECTORY = Path(os.getenv('APP_HOME')).resolve()
ERES_USERNAME = os.getenv('ERES_USERNAME')
ERES_PASSWORD = os.getenv('ERES_PASSWORD')

SCREENSHOT_FOLDER = HOME_DIRECTORY / Path('pass_list_screenshots')
SCREENSHOT_FOLDER.mkdir(exist_ok=True)

database_connection = sqlite3.connect(str(HOME_DIRECTORY / Path('data.db')))
cursor = database_connection.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS `data` (
    `id` INTEGER PRIMARY KEY,
    `data_timestamp`,
    `hash`,
    `flight_no`,
    `origin`,
    `destination`,
    `date`,
    `day_of_week`,
    `flight_time`,
    `av_bu`,
    `av_co`,
    `av_pp`,
    `av_to`,
    `ca_bu`,
    `ca_co`,
    `ca_pp`,
    `ca_to`,
    `au_bu`,
    `au_co`,
    `au_pp`,
    `au_to`,
    `bo_bu`,
    `bo_co`,
    `bo_pp`,
    `bo_to`,
    `ps_bu`,
    `ps_co`,
    `ps_pp`,
    `ps_to`,
    `sa_bu`,
    `sa_co`,
    `sa_pp`,
    `sa_to`,
    `he_bu`,
    `he_co`,
    `he_pp`,
    `he_to`,
    `gr_bu`,
    `gr_co`,
    `gr_pp`,
    `gr_to`,
    `re_bu`,
    `re_co`,
    `re_pp`,
    `re_to`,
    `pos_va`,
    `pos_pe`,
    `flight_raw`,
    `pass_rider_raw`
)
''')
database_connection.commit()

def fetch_flight(origin, destination, depart_date):
    flight_search_result, pass_rider_result, pass_rider_screenshot = fetch(ERES_USERNAME, ERES_PASSWORD, origin, destination, depart_date, logger)

    flight = flight_search_result['AvailableRoutes']['Routes'][0]['Segments'][0]
    pass_rider_list = pass_rider_result['PassengerList']

    flight_no = flight['FlightNumber']
    returned_origin = flight['Origin']['AirportCode']
    returned_destination = flight['Destination']['AirportCode']
    returned_departure_date = flight['DepartureDate']
    departure_time = flight['DepartureTime']
    available = flight['Available']
    capacity = flight['Capacity']
    authorized = flight['Authorized']
    booked = flight['Booked']
    positive_space = flight['PS']
    sa_listed = flight['SA']
    held = flight['Held']
    group = flight['Group']
    rev_standby = flight['RSB']

    pass_position_vacation = ''
    pass_position_personal = ''
    for passenger in pass_rider_list:
        if passenger['PassClass'] == 'Unaccompanied traveler - Vacation ePass':
            pass_position_vacation = passenger['Position']
        elif passenger['PassClass'] == 'Unaccompanied traveler - Personal ePass':
            pass_position_personal = passenger['Position']
    
    return {
        'flight_no': flight_no,
        'returned_origin': returned_origin,
        'returned_destination': returned_destination,
        'returned_departure_date': returned_departure_date,
        'departure_time': departure_time,
        'available': available,
        'capacity': capacity,
        'authorized': authorized,
        'booked': booked,
        'positive_space': positive_space,
        'sa_listed': sa_listed,
        'held': held,
        'group': group,
        'rev_standby': rev_standby,
        'pass_position_vacation': pass_position_vacation,
        'pass_position_personal': pass_position_personal,
        'flight_raw': flight,
        'pass_rider_raw': pass_rider_list,
        'pass_rider_screenshot': pass_rider_screenshot
    }

def search_and_cache(origin, destination):
    today = datetime.today()

    data = fetch_flight(origin, destination, today)

    hash = encode.encode(data['flight_no'], data['returned_departure_date'], data['returned_origin'], data['returned_destination'])
    timestamp = int(time.time())
    day_of_week = datetime.strptime(data['returned_departure_date'], '%m/%d/%Y').weekday()

    cursor.execute(INSERT_STATEMENT, 
        (
            timestamp,
            hash,
            data['flight_no'],
            data['returned_origin'],
            data['returned_destination'],
            data['returned_departure_date'],
            int(day_of_week),
            data['departure_time'],
            int(data['available']['Business']),
            int(data['available']['Coach']),
            int(data['available']['PremiumPlus']),
            int(data['available']['Total']),
            int(data['capacity']['Business']),
            int(data['capacity']['Coach']),
            int(data['capacity']['PremiumPlus']),
            int(data['capacity']['Total']),
            int(data['authorized']['Business']),
            int(data['authorized']['Coach']),
            int(data['authorized']['PremiumPlus']),
            int(data['authorized']['Total']),
            int(data['booked']['Business']),
            int(data['booked']['Coach']),
            int(data['booked']['PremiumPlus']),
            int(data['booked']['Total']),
            int(data['positive_space']['Business']),
            int(data['positive_space']['Coach']),
            int(data['positive_space']['PremiumPlus']),
            int(data['positive_space']['Total']),
            int(data['sa_listed']['Business']),
            int(data['sa_listed']['Coach']),
            int(data['sa_listed']['PremiumPlus']),
            int(data['sa_listed']['Total']),
            int(data['held']['Business']),
            int(data['held']['Coach']),
            int(data['held']['PremiumPlus']),
            int(data['held']['Total']),
            int(data['group']['Business']),
            int(data['group']['Coach']),
            int(data['group']['PremiumPlus']),
            int(data['group']['Total']),
            int(data['rev_standby']['Business']),
            int(data['rev_standby']['Coach']),
            int(data['rev_standby']['PremiumPlus']),
            int(data['rev_standby']['Total']),
            int(data['pass_position_vacation']),
            int(data['pass_position_personal']),
            json.dumps(data['flight_raw']),
            json.dumps(data['pass_rider_raw'])
        )
    )
    database_connection.commit()

    screenshot_path = str(SCREENSHOT_FOLDER / Path(f'{hash}.png'))
    with open(screenshot_path, 'wb') as f:
        f.write(data['pass_rider_screenshot'])

    logger.info(f'Fetched and added flight UAL{data["flight_raw"]["FlightNumber"]} {origin}-{destination} departing {data["flight_raw"]["DepartureDate"]} at {data["flight_raw"]["DepartureTime"]} to database.')

search_and_cache(sys.argv[1], sys.argv[2])