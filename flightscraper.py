import os
import time
from datetime import datetime
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, MetaData
from PIL import Image
import encode
from fetch import fetch

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
MYSQL_IP = os.getenv('MYSQL_IP')
MYSQL_PORT = os.getenv('MYSQL_PORT')
MYSQL_USERNAME = os.getenv('MYSQL_USERNAME')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_TABLE = os.getenv('MYSQL_TABLE')

SCREENSHOT_FOLDER = HOME_DIRECTORY / Path('pass_list_screenshots')
SCREENSHOT_FOLDER.mkdir(exist_ok=True)

engine = create_engine(f'mysql+mysqldb://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_IP}:{MYSQL_PORT}/data')
data_table = Table(MYSQL_TABLE, MetaData(), autoload_with=engine)

def fetch_flight(origin, destination):
    flight_search_result, pass_rider_result, pass_rider_screenshot = fetch(ERES_USERNAME, ERES_PASSWORD, origin, destination)

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
    data = fetch_flight(origin, destination)

    hash = encode.encode(data['flight_no'], data['returned_departure_date'], data['returned_origin'], data['returned_destination'])
    timestamp = int(time.time())
    returned_date = datetime.strptime(data['returned_departure_date'], '%m/%d/%Y')
    day_of_week = returned_date.weekday()

    insert_statement = data_table.insert().values( 
        hash=hash,
        data_timestamp=timestamp,
        flight_no=data['flight_no'],
        origin=data['returned_origin'],
        destination=data['returned_destination'],
        date=returned_date.strftime('%Y-%m-%d'),
        day_of_week=int(day_of_week),
        flight_time=data['departure_time'],
        av_bu=int(data['available']['Business']),
        av_co=int(data['available']['Coach']),
        av_pp=int(data['available']['PremiumPlus']),
        av_to=int(data['available']['Total']),
        ca_bu=int(data['capacity']['Business']),
        ca_co=int(data['capacity']['Coach']),
        ca_pp=int(data['capacity']['PremiumPlus']),
        ca_to=int(data['capacity']['Total']),
        au_bu=int(data['authorized']['Business']),
        au_co=int(data['authorized']['Coach']),
        au_pp=int(data['authorized']['PremiumPlus']),
        au_to=int(data['authorized']['Total']),
        bo_bu=int(data['booked']['Business']),
        bo_co=int(data['booked']['Coach']),
        bo_pp=int(data['booked']['PremiumPlus']),
        bo_to=int(data['booked']['Total']),
        ps_bu=int(data['positive_space']['Business']),
        ps_co=int(data['positive_space']['Coach']),
        ps_pp=int(data['positive_space']['PremiumPlus']),
        ps_to=int(data['positive_space']['Total']),
        sa_bu=int(data['sa_listed']['Business']),
        sa_co=int(data['sa_listed']['Coach']),
        sa_pp=int(data['sa_listed']['PremiumPlus']),
        sa_to=int(data['sa_listed']['Total']),
        he_bu=int(data['held']['Business']),
        he_co=int(data['held']['Coach']),
        he_pp=int(data['held']['PremiumPlus']),
        he_to=int(data['held']['Total']),
        gr_bu=int(data['group']['Business']),
        gr_co=int(data['group']['Coach']),
        gr_pp=int(data['group']['PremiumPlus']),
        gr_to=int(data['group']['Total']),
        re_bu=int(data['rev_standby']['Business']),
        re_co=int(data['rev_standby']['Coach']),
        re_pp=int(data['rev_standby']['PremiumPlus']),
        re_to=int(data['rev_standby']['Total']),
        pos_va=int(data['pass_position_vacation']),
        pos_pe=int(data['pass_position_personal']),
        flight_raw=json.dumps(data['flight_raw']),
        pass_rider_raw=json.dumps(data['pass_rider_raw'])
    )
    
    with engine.connect() as connection:
        connection.execute(insert_statement)
        connection.commit()

    # Seleniumbase captures a little past the pass rider list to the left, so crop the extra space off the left to match the images that were captured previously
    original_screenshot_path = data['pass_rider_screenshot']
    screenshot = Image.open(original_screenshot_path)
    width, height = screenshot.size
    cropped_screenshot = screenshot.crop((7, 0, width, height))

    new_screenshot_path = SCREENSHOT_FOLDER / Path(f'{hash}.png')
    cropped_screenshot.save(new_screenshot_path)

    os.remove(original_screenshot_path)

    logger.info(f'Fetched and added flight UAL{data["flight_raw"]["FlightNumber"]} {origin}-{destination} departing {data["flight_raw"]["DepartureDate"]} at {data["flight_raw"]["DepartureTime"]} to database.')

search_and_cache(sys.argv[1], sys.argv[2])