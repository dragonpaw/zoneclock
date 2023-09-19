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
import rtc

from _secrets import secrets

WIFI_TEST_URL = "http://wifitest.adafruit.com/testwifi/index.html"


class BasicApp:
    """Provides the common app setup and functionality."""

    def __init__(self):
        self.brightness = 1.00
        self.board = board
        self.cron_jobs = {}
        self._cron_last_ran = {}
        self.status_label = None

    def set_boot_status(self, msg: str):
        """Set the on-boot status, if it's still being displayed."""
        if self.status_label:
            self.status_label.text = msg.replace(" ", "\n")

    def cron_run(self):
        """Check for and run due cron jobs.

        Cron jobs are defined as a dict of method names, to intervals(in seconds)
        they should run."""

        now = time.time()
        for job in self.cron_jobs:
            if job not in self._cron_last_ran or (
                self._cron_last_ran[job] + self.cron_jobs[job] < now
            ):
                print(f"Running scheduled job: {job}")
                getattr(self, job)()
                self._cron_last_ran[job] = now

    def network_setup(self) -> ESPSPI_WiFiManager:
        """Activate the WiFi network."""

        self.set_boot_status("WiFi Setup")

        esp32_cs = DigitalInOut(board.ESP_CS)
        esp32_ready = DigitalInOut(board.ESP_BUSY)
        esp32_reset = DigitalInOut(board.ESP_RESET)
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

        self.network = ESPSPI_WiFiManager(
            esp,
            secrets,
            status_pixel=neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2),
            debug=True,
        )
        self.network_test()

    def network_test(self):
        """Test that the network is working by fetching and printing data."""

        self.set_boot_status("WiFi Test")

        print("Fetching text from", WIFI_TEST_URL)
        r = self.network.get(WIFI_TEST_URL)
        print("-" * 40)
        print(r.text)
        print("-" * 40)
        r.close()

        print("Done!")

    def parse_time(self, timestring: str, is_dst=-1):
        """Given a string of the format YYYY-MM-DDTHH:MM:SS.SS-HH:MM (and
        optionally a DST flag), convert to and return an equivalent
        time.struct_time (strptime() isn't available here). Calling function
        can use time.mktime() on result if epoch seconds is needed instead.
        Time string is assumed local time; UTC offset is ignored. If seconds
        value includes a decimal fraction it's ignored.
        """

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

    def lookup_timezone(self, name: str, set_rtc=False):
        """Update system date/time from WorldTimeAPI public server;
        no account required. Pass in time zone string
        (http://worldtimeapi.org/api/timezone for list)
        or None to use IP geolocation. Returns current local time as a
        time.struct_time and UTC offset as string. This may throw an
        exception on fetch_data() - it is NOT CAUGHT HERE, should be
        handled in the calling code because different behaviors may be
        needed in different situations (e.g. reschedule for later).
        """

        time_url = f"http://worldtimeapi.org/api/timezone/{name}"

        print(f"Fetching time from {time_url}...")
        time_data: dict = self.network.get(
            time_url, headers={"Accept": "application/json"}
        ).json()

        # This is here because we sync the clock via the same API as lookup TZ offsets.
        if set_rtc:
            time_struct = self.parse_time(
                timestring=time_data["datetime"], is_dst=time_data["dst"]
            )
            old_time = time.time()
            rtc.RTC().datetime = time_struct
            print(
                "RTC updated from Internet: {0}, change was: {1}s".format(
                    time.localtime(), old_time - time.time()
                )
            )

        delta = timedelta(seconds=time_data["raw_offset"])
        if time_data["dst"]:
            delta += timedelta(seconds=time_data["dst_offset"])
        print("{:20s} {:d}".format(time_data["timezone"], delta.seconds))
        return timezone(offset=delta, name=time_data["timezone"])

    def color(self, color_in_hex: int) -> int:
        """Apply brightness to a color.

        This is the math you do when the board don't support brightness setting.
        """

        r = int(round((color_in_hex >> 16) * self.brightness, 0))
        g = int(round((color_in_hex >> 8 & 0xFF) * self.brightness, 0))
        b = int(round((color_in_hex & 0xFF) * self.brightness, 0))
        # print(f"r:{r}, g:{g}, b:{b}")
        return r << 16 | g << 8 | b
