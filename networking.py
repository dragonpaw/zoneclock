import time

import board
import busio
import neopixel
from adafruit_esp32spi.adafruit_esp32spi_wifimanager import (
    ESPSPI_WiFiManager,
    adafruit_esp32spi,
)
from adafruit_datetime import timezone, timedelta
from digitalio import DigitalInOut

from _secrets import secrets

WIFI_TEST_URL = "http://wifitest.adafruit.com/testwifi/index.html"


def network_setup() -> ESPSPI_WiFiManager:
    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    manager = ESPSPI_WiFiManager(
        esp,
        secrets,
        status_pixel=neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2),
        debug=True,
    )
    return manager


def network_test(requests: ESPSPI_WiFiManager):
    """Test that the network is working by fetching and printing data"""
    # esp._debug = True
    print("Fetching text from", WIFI_TEST_URL)
    r = requests.get(WIFI_TEST_URL)
    print("-" * 40)
    print(r.text)
    print("-" * 40)
    r.close()

    print("Done!")


def parse_time(timestring, is_dst=-1):
    """Given a string of the format YYYY-MM-DDTHH:MM:SS.SS-HH:MM (and
    optionally a DST flag), convert to and return an equivalent
    time.struct_time (strptime() isn't available here). Calling function
    can use time.mktime() on result if epoch seconds is needed instead.
    Time string is assumed local time; UTC offset is ignored. If seconds
    value includes a decimal fraction it's ignored.
    """
    import time

    date_time = timestring.split("T")  # Separate into date and time
    year_month_day = date_time[0].split("-")  # Separate time into Y/M/D
    hour_minute_second = date_time[1].split("+")[0].split("-")[0].split(":")
    return time.struct_time(
        (
            int(year_month_day[0]),
            int(year_month_day[1]),
            int(year_month_day[2]),
            int(hour_minute_second[0]),
            int(hour_minute_second[1]),
            int(hour_minute_second[2].split(".")[0]),
            -1,
            -1,
            is_dst,
        )
    )


def lookup_timezone(requests: ESPSPI_WiFiManager, name: str, set_rtc=False):
    """Update system date/time from WorldTimeAPI public server;
    no account required. Pass in time zone string
    (http://worldtimeapi.org/api/timezone for list)
    or None to use IP geolocation. Returns current local time as a
    time.struct_time and UTC offset as string. This may throw an
    exception on fetch_data() - it is NOT CAUGHT HERE, should be
    handled in the calling code because different behaviors may be
    needed in different situations (e.g. reschedule for later).
    """
    import rtc

    time_url = f"http://worldtimeapi.org/api/timezone/{name}"

    print(f"Fetching time from {time_url}...")
    time_data: dict = requests.get(
        time_url, headers={"Accept": "application/json"}
    ).json()
    if set_rtc:
        time_struct = parse_time(
            timestring=time_data["datetime"], is_dst=time_data["dst"]
        )
        rtc.RTC().datetime = time_struct
        print("RTC updated from Internet: %s" % time.localtime())
    delta = timedelta(seconds=time_data["raw_offset"])
    if time_data["dst"]:
        delta += timedelta(seconds=time_data["dst_offset"])
    print("{:20s} {:d}".format(time_data["timezone"], delta.seconds))
    return timezone(offset=delta, name=time_data["timezone"])
