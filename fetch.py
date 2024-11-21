import asyncio
import base64
import json

from seleniumbase.undetected import cdp_driver
import mycdp

USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
PASSRIDER_LOGIN = '**REDACTED**'
API_URL = '**REDACTED**'

class Fetch:
    def __init__(self, browser: cdp_driver.browser.Browser, eres_username: str, eres_password: str, origin: str, destination: str):
        self._browser = browser
        self._eres_username = eres_username
        self._eres_password = eres_password
        self._origin = origin
        self._destination = destination
        self._tab = None
        self._running_tasks = set()
        self._responses = []
        self._screenshot_path = ''

    async def start(self):
        self._tab = await self._browser.get(PASSRIDER_LOGIN, new_tab=True)
        self._tab.add_handler(mycdp.fetch.RequestPaused, self._handle_request_paused)
        await self._tab.send(mycdp.fetch.enable([
            mycdp.fetch.RequestPattern(
                url_pattern=API_URL,
                request_stage=mycdp.fetch.RequestStage(
                    value='Response'
                )
            )
        ]))
        await self._tab.wait(t=1)
        await self._perform_actions()

    async def _perform_actions(self):
        username_element = await self._tab.select('input#userName')
        await username_element.send_keys_async(self._eres_username)

        await self._tab.wait(t=1)

        password_element = await self._tab.select('input#password')
        await password_element.send_keys_async(self._eres_password)

        await self._tab.wait(t=1)

        submit_button = await self._tab.select('button.submit')
        await submit_button.mouse_click_async()

        await self._tab.wait(t=3)

        accept_button = await self._tab.select('[class*="src-components-Modal-termsConditions__secondaryButton"]', timeout=20)
        await accept_button.mouse_click_async()

        await self._tab.wait(t=2)

        origin_input = await self._tab.select('input#bookFlightOriginInput')
        await origin_input.mouse_click_async()

        await self._tab.wait(t=1)

        await origin_input.send_keys_async(self._origin)

        await self._tab.wait(t=0.5)

        origin_fill = await self._tab.select('button#listBtn0', timeout=5)
        await origin_fill.mouse_click_async()

        await self._tab.wait(t=1)

        dest_input = await self._tab.select('input#bookFlightDestinationInput')
        await dest_input.mouse_click_async()

        await self._tab.wait(t=1)

        await dest_input.send_keys_async(self._destination)

        await self._tab.wait(t=0.5)

        dest_fill = await self._tab.select('button#listBtn0', timeout=5)
        await dest_fill.mouse_click_async()

        await self._tab.wait(t=1)

        calendar_button = await self._tab.select('button.SingleDatePickerInput_calendarIcon')
        await calendar_button.mouse_click_async()

        await self._tab.wait(t=0.5)

        today_button = await self._tab.select('td.CalendarDay__today button.CalendarDay_button')
        await today_button.mouse_click_async()

        await self._tab.wait(t=1)

        search_button = await self._tab.select('[class*="src-components-SearchFlightForm-searchFlightForm__secondaryButton"]')
        await search_button.mouse_click_async()

        await self._tab.wait(t=3)

        flight_rows = await self._tab.select_all('[class*="Collapsible src-components-FSRDetailsComponent-FSRDetailsComponent__detailsCollapsible"]', timeout=5)
        flight_row = flight_rows[0]
        await flight_row.mouse_click_async()

        await self._tab.wait(t=2)

        standby_list = await self._tab.select('div#fsrTabs-pane-1', timeout=10)
        self._screenshot_path = await standby_list.save_screenshot_async()
    

    async def stop(self):
        await self._tab.close()
    

    def _handle_xhr_response(self, task):
        payload, is_encoded = task.result()
        try:
            if is_encoded:
                decoded_body = base64.b64decode(payload)
                payload = json.loads(decoded_body)
                self._responses.append(payload)
        finally:
            self._running_tasks.remove(task)


    async def _handle_request_paused(self, event: mycdp.fetch.RequestPaused, event_tab: cdp_driver.tab.Tab):
        if event.response_status_code == 200:
            print(f'Got request: {event.request.url}   {event.response_status_code}   {event.request_id}')

            task = asyncio.create_task(event_tab.send(mycdp.fetch.get_response_body(request_id=event.request_id)))
            self._running_tasks.add(task)

            task.add_done_callback(self._handle_xhr_response)

        event_tab.feed_cdp(mycdp.fetch.continue_response(request_id=event.request_id))


async def fetch_async(eres_username, eres_password, origin, destination):
    browser = await cdp_driver.cdp_util.start_async(headless=True, browser_args=[f'--user-agent="{USER_AGENT}"'])

    interceptor = Fetch(browser, eres_username, eres_password, origin, destination)
    await interceptor.start()

    responses = interceptor._responses
    screenshot_url = interceptor._screenshot_path

    await interceptor.stop()

    browser.stop()
    
    return responses, screenshot_url


def fetch(eres_username, eres_password, origin, destination):
    event_loop = asyncio.get_event_loop()
    result = event_loop.run_until_complete(fetch_async(eres_username, eres_password, origin, destination))

    flight_search_result = result[0][2]
    pass_rider_result = result[0][4]
    pass_rider_screenshot = result[1]

    return flight_search_result, pass_rider_result, pass_rider_screenshot