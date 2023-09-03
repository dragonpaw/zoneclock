# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# import time
# import board
# import busio
# from digitalio import DigitalInOut
# import neopixel
# from adafruit_esp32spi import adafruit_esp32spi
# from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import gc
import time
import displayio
from rtc import RTC
from adafruit_matrixportal.matrix import Matrix
from adafruit_bitmap_font import bitmap_font
import adafruit_display_text.label

# Get wifi details and more from a secrets.py file
try:
    from _secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print(f"secrets loaded: {secrets}")

# CONFIGURABLE SETTINGS ----------------------------------------------------

TWELVE_HOUR = True  # If set, use 12-hour time vs 24-hour (e.g. 3:00 vs 15:00)
COUNTDOWN = False  # If set, show time to (vs time of) next rise/set event
MONTH_DAY = True  # If set, use MM/DD vs DD/MM (e.g. 31/12 vs 12/31)
BITPLANES = 6  # Ideally 6, but can set lower if RAM is tight

WIFI_TEST_URL = "http://wifitest.adafruit.com/testwifi/index.html"


# def parse_time(timestring, is_dst=-1):
#     """Given a string of the format YYYY-MM-DDTHH:MM:SS.SS-HH:MM (and
#     optionally a DST flag), convert to and return an equivalent
#     time.struct_time (strptime() isn't available here). Calling function
#     can use time.mktime() on result if epoch seconds is needed instead.
#     Time string is assumed local time; UTC offset is ignored. If seconds
#     value includes a decimal fraction it's ignored.
#     """
#     date_time = timestring.split("T")  # Separate into date and time
#     year_month_day = date_time[0].split("-")  # Separate time into Y/M/D
#     hour_minute_second = date_time[1].split("+")[0].split("-")[0].split(":")
#     return time.struct_time(
#         (
#             int(year_month_day[0]),
#             int(year_month_day[1]),
#             int(year_month_day[2]),
#             int(hour_minute_second[0]),
#             int(hour_minute_second[1]),
#             int(hour_minute_second[2].split(".")[0]),
#             -1,
#             -1,
#             is_dst,
#         )
#     )


# def update_time(timezone=None):
#     """Update system date/time from WorldTimeAPI public server;
#     no account required. Pass in time zone string
#     (http://worldtimeapi.org/api/timezone for list)
#     or None to use IP geolocation. Returns current local time as a
#     time.struct_time and UTC offset as string. This may throw an
#     exception on fetch_data() - it is NOT CAUGHT HERE, should be
#     handled in the calling code because different behaviors may be
#     needed in different situations (e.g. reschedule for later).
#     """
#     if timezone:  # Use timezone api
#         time_url = f"http://worldtimeapi.org/api/timezone/{timezone}"
#     else:  # Use IP geolocation
#         time_url = "http://worldtimeapi.org/api/ip"

#     print(f"Fetching time from {time_url}...")
#     time_data = NETWORK.fetch_data(
#         time_url, json_path=[["datetime"], ["dst"], ["utc_offset"]]
#     )
#     time_struct = parse_time(time_data[0], time_data[1])
#     RTC().datetime = time_struct
#     print("Time synced to: %s" % time_struct)
#     return time_struct, time_data[2]


def hh_mm(time_struct):
    """Given a time.struct_time, return a string as H:MM or HH:MM, either
    12- or 24-hour style depending on global TWELVE_HOUR setting.
    This is ONLY for 'clock time,' NOT for countdown time, which is
    handled separately in the one spot where it's needed.
    """
    if TWELVE_HOUR:
        if time_struct.tm_hour > 12:
            hour_string = str(time_struct.tm_hour - 12)  # 13-23 -> 1-11 (pm)
        elif time_struct.tm_hour > 0:
            hour_string = str(time_struct.tm_hour)  # 1-12
        else:
            hour_string = "12"  # 0 -> 12 (am)
    else:
        hour_string = "{0:0>2}".format(time_struct.tm_hour)
    return hour_string + ":" + "{0:0>2}".format(time_struct.tm_min)


# def network_setup():
#     """Initialize the internet connection and set the time"""

#     import board
#     from adafruit_matrixportal.network import Network

#     network = Network(status_neopixel=board.NEOPIXEL, debug=True)

#     network.connect()
#     network._wifi.esp.reset()
#     time.sleep(1)
#     print(f"Network connected: {network.is_connected}, {network.ip_address}")

#     network.requests.get(WIFI_TEST_URL)
#     print("Network test passed")

#     # Set time
#     try:
#         network.get_local_time()
#     except RuntimeError as e:
#         print("Some error occured, retrying! -", e)
#         wifi_reset(network)
#         network.get_local_time()

#     return network


# ONE-TIME INITIALIZATION --------------------------------------------------

NETWORK = network_setup()

MATRIX = Matrix(bit_depth=BITPLANES)
DISPLAY = MATRIX.display

# ACCEL = adafruit_lis3dh.LIS3DH_I2C(busio.I2C(board.SCL, board.SDA), address=0x19)
# _ = ACCEL.acceleration  # Dummy reading to blow out any startup residue
# time.sleep(0.1)
# DISPLAY.rotation = (
#     int(
#         (
#             (math.atan2(-ACCEL.acceleration.y, -ACCEL.acceleration.x) + math.pi)
#             / (math.pi * 2)
#             + 0.875
#         )
#         * 4
#     )
#     % 4
# ) * 90
# print(f"Display rotation: {DISPLAY.rotation}")

LARGE_FONT = bitmap_font.load_font("/fonts/helvB12.bdf")
SMALL_FONT = bitmap_font.load_font("/fonts/helvR10.bdf")
SYMBOL_FONT = bitmap_font.load_font("/fonts/6x10.bdf")
LARGE_FONT.load_glyphs("0123456789:")
SMALL_FONT.load_glyphs("0123456789:/.%")
SYMBOL_FONT.load_glyphs("\u21A5\u21A7")
print("Fonts loaded")

# Display group is set up once, then we just shuffle items around later.
# Order of creation here determines their stacking order.
GROUP = displayio.Group()

# # Element 0 is a stand-in item, later replaced with the moon phase bitmap
# # pylint: disable=bare-except
# try:
#     FILENAME = "moon/splash-" + str(DISPLAY.rotation) + ".bmp"

#     # CircuitPython 6 & 7 compatible
#     BITMAP = displayio.OnDiskBitmap(open(FILENAME, "rb"))
#     TILE_GRID = displayio.TileGrid(
#         BITMAP, pixel_shader=getattr(BITMAP, "pixel_shader", displayio.ColorConverter())
#     )

#     # # CircuitPython 7+ compatible
#     # BITMAP = displayio.OnDiskBitmap(FILENAME)
#     # TILE_GRID = displayio.TileGrid(BITMAP, pixel_shader=BITMAP.pixel_shader)

#     GROUP.append(TILE_GRID)
# except:
#     GROUP.append(
#         adafruit_display_text.label.Label(SMALL_FONT, color=0xFF0000, text="AWOO")
#     )
#     GROUP[0].x = (DISPLAY.width - GROUP[0].bounding_box[2] + 1) // 2
#     GROUP[0].y = DISPLAY.height // 2 - 1
# print("Splash loaded")

# Elements 1-4 are an outline around the moon percentage -- text labels
# offset by 1 pixel up/down/left/right. Initial position is off the matrix,
# updated on first refresh. Initial text value must be long enough for
# longest anticipated string later.
for i in range(4):
    GROUP.append(
        adafruit_display_text.label.Label(SMALL_FONT, color=0, text="99.9%", y=-99)
    )
# Element 5 is the moon percentage (on top of the outline labels)
GROUP.append(
    adafruit_display_text.label.Label(SMALL_FONT, color=0xFFFF00, text="99.9%", y=-99)
)
# Element 6 is the current time
GROUP.append(
    adafruit_display_text.label.Label(LARGE_FONT, color=0x808080, text="12:00", y=-99)
)
# Element 7 is the current date
GROUP.append(
    adafruit_display_text.label.Label(SMALL_FONT, color=0x808080, text="12/31", y=-99)
)
# Element 8 is a symbol indicating next rise or set
# GROUP.append(
#     adafruit_display_text.label.Label(SYMBOL_FONT, color=0x00FF00, text="x", y=-99)
# )
# # Element 9 is the time of (or time to) next rise/set event
# GROUP.append(
#     adafruit_display_text.label.Label(SMALL_FONT, color=0x00FF00, text="12:00", y=-99)
# )
DISPLAY.show(GROUP)
print("Splash displayed")

# Set initial clock time, also fetch initial UTC offset while
# here (NOT stored in secrets.py as it may change with DST).
# pylint: disable=bare-except

TIMEZONE = secrets["timezone"]  # e.g. 'America/New_York'

# Poll server for moon data for current 24-hour period and +24 ahead
# PERIOD = []
# for DAY in range(2):
#     PERIOD.append(MoonData(DATETIME, DAY * 24, UTC_OFFSET))
# PERIOD[0] is the current 24-hour time period we're in. PERIOD[1] is the
# following 24 hours. Data is shifted down and new data fetched as days
# expire. Thought we might need a PERIOD[2] for certain circumstances but
# it appears not, that's changed easily enough if needed.


# ---------------------------------------------------------------------------- #
#                                     Main                                     #
# ---------------------------------------------------------------------------- #
def main():
    LAST_SYNC = 0  # Time of last sync attempt
    while True:
        print("Loop start")
        gc.collect()
        NOW = time.time()  # Current epoch time in seconds

        # Sync with time server every ~12 hours
        if NOW - LAST_SYNC > 12 * 60 * 60:
            try:
                DATETIME, UTC_OFFSET = update_time(TIMEZONE)
                LAST_SYNC = time.mktime(DATETIME)
                continue  # Time may have changed; refresh NOW value
            except Exception as exc:
                print(f"Time sync error: {exc}, will retry")
                wifi_reset(NETWORK)
                if LAST_SYNC == 0:
                    raise  # On first run, fail hard
                # update_time() can throw an exception if time server doesn't
                # respond. That's OK, keep running with our current time, and
                # push sync time ahead to retry in 30 minutes (don't overwhelm
                # the server with repeated queries).
                LAST_SYNC += 30 * 60  # 30 minutes -> seconds

        CENTER_X = DISPLAY.width // 2
        TIME_Y = DISPLAY.height // 2 - 1

        # Update time (GROUP[6]) and date (GROUP[7])
        NOW = time.localtime()
        STRING = hh_mm(NOW)
        GROUP[6].text = STRING
        GROUP[6].x = CENTER_X - GROUP[6].bounding_box[2] // 2
        GROUP[6].y = TIME_Y
        if MONTH_DAY:
            STRING = str(NOW.tm_mon) + "/" + str(NOW.tm_mday)
        else:
            STRING = str(NOW.tm_mday) + "/" + str(NOW.tm_mon)
        GROUP[7].text = STRING
        GROUP[7].x = CENTER_X - GROUP[7].bounding_box[2] // 2
        GROUP[7].y = TIME_Y + 10
        print(f"Time updated: {STRING}")
        DISPLAY.refresh()  # Force full repaint (splash screen sometimes sticks)
        print("Display refreshed")
        time.sleep(5)


if __name__ == "__main__":
    main()
