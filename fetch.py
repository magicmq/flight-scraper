import time
import json
import gzip

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import TimeoutException

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
PASSRIDER_LOGIN = '**REDACTED**'
FLIGHT_SEARCH_REQUEST = '**REDACTED**'
PASS_RIDER_REQUEST = '**REDACTED**'

def decode_response_body(request):
    if request.response.headers.get('content-encoding') == 'gzip':
        return gzip.decompress(request.response.body).decode('utf-8')
    else:
        return request.response.body.decode('utf-8')

def fetch(eres_username, eres_password, origin, destination, date, logger):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--user-agent={USER_AGENT}')
    chrome_options.add_argument('--window-size=1920,3000')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    seleniumwire_options = {
        'request_storage': 'memory',
        'exclude_hosts': ['accounts.google.com', 'content-autofill.googleapis.com', 'optimizationguide-pa.googleapis.com', 'ingest.quantummetric.com', 'rl.quantummetric.com', 'cdn.quantummetric.com', 'tags.tiqcdn.com', 'google-analytics.com', 'www.google-analytics.com', 'www.googletagmanager.com']
    }
    driver = webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)

    driver.scopes = [
        '**REDACTED**'
    ]

    driver.get(PASSRIDER_LOGIN)
    driver.find_element(By.ID, 'userName').send_keys(eres_username)
    driver.find_element(By.ID, 'password').send_keys(eres_password)
    driver.find_element(By.XPATH, '//button[normalize-space()="Sign in"]').click()

    try:
        accept_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space()="Accept"]')))
        accept_button.click()
    except TimeoutException:
        logger.exception('Unable to locate button to accept terms and conditions. Exiting...')
        exit(1)

    time.sleep(0.5)

    origin_field = driver.find_element(By.ID, 'bookFlightOriginInput')
    origin_field.send_keys(origin)
    origin_field.send_keys(Keys.TAB)

    destination_field = driver.find_element(By.ID, 'bookFlightDestinationInput')
    destination_field.send_keys(destination)
    destination_field.send_keys(Keys.TAB)

    driver.find_element(By.ID, 'oneWayIcon').click()

    today_string = date.strftime('%A, %B %d, %Y')
    driver.find_element(By.CSS_SELECTOR, f'[aria-label="{today_string}').click()

    driver.find_element(By.XPATH, '//button[normalize-space()="Search"]').click()

    try:
        rows = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[class*="src-components-FSRDetailsComponent-FSRDetailsComponent__entireRow"]'))
        )
    except TimeoutException:
        logger.exception('Unable to locate flight row in search results. Exiting...')
        exit(1)

    flight_row = rows[0]

    flight_row.find_element(By.CSS_SELECTOR, '[class*="Collapsible src-components-FSRDetailsComponent-FSRDetailsComponent__detailsCollapsible"]').click()

    try:
        standby_list = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'fsrTabs-pane-1')))
    except TimeoutException:
        logger.exception('Unable to locate pass rider list pane. Exiting...')
        exit(1)

    time.sleep(1)

    pass_rider_screenshot = standby_list.screenshot_as_png

    flight_search_result = None
    pass_rider_result = None
    for request in driver.requests:
        if request.url == FLIGHT_SEARCH_REQUEST:
            flight_search_result = decode_response_body(request)
        elif request.url == PASS_RIDER_REQUEST:
            pass_rider_result = decode_response_body(request)

    flight_search_result = json.loads(flight_search_result)
    pass_rider_result = json.loads(pass_rider_result)

    driver.quit()

    return flight_search_result, pass_rider_result, pass_rider_screenshot