# pyright: reportShadowedImports=false
# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Ash's multi-TZ wall clock
"""

import gc
import time
import displayio
import terminalio
from adafruit_datetime import datetime
from adafruit_display_text.label import Label
from adafruit_matrixportal.matrix import Matrix
from adafruit_datetime import timezone

import colors2 as colors
import basic

TIMEZONES_to_SHOW = [
    "America/Los_Angeles",
    "Europe/Berlin",
    "Europe/Athens",
    "Asia/Kuala_Lumpur",
]

COUNTRY_CODES = {
    "America/Los_Angeles": "US",
    "Europe/Berlin": "DE",
    "Europe/Athens": "GR",
    "Asia/Kuala_Lumpur": "MY",
}

FLAG_COLORS = {
    "US": [colors.RED, colors.WHITE, colors.BLUE],
    "DE": [colors.GRAY, colors.RED, colors.GOLD],
    "GR": [colors.BLUE, colors.WHITE, colors.BLUE],
    "MY": [colors.YELLOW, colors.BLUE, colors.RED],
}


class ZoneClock(basic.BasicApp):
    """A clock for showing 4 time zones on a 32x32 display."""

    def __init__(self, timezone_names: list[str]) -> None:
        super().__init__()

        # Board level variables
        self.matrix = Matrix(bit_depth=6, width=32, height=32)
        self.display = self.matrix.display
        self.brightness = 0.2
        self.display.brightness = self.brightness  # Doesn't seem to do anything sadly.

        # The sadly ugly font we use
        self.font = terminalio.FONT
        self.line_spacing = 0.75

        # The zones we will be monitoring.
        self.timezone_names = timezone_names

        # The display group to use for the life of the app
        self.display_group: displayio.Group = displayio.Group(x=2, y=0)
        self.display.root_group = self.display_group

        # The status label we will update while starting up.
        self.status_label = Label(
            self.font,
            text="Booting",
            color=self.color(colors.ORCHID),
            x=0,
            y=10,
            line_spacing=self.line_spacing,
        )
        self.display_group.append(self.status_label)

        # WiFi setup
        self.status_label.color = self.color(colors.PURPLE)
        self.status_label.text = "WiFi\nSetup"
        self.network_setup()

        # Network test
        self.status_label.text = "WiFi\nTest"
        self.network_test()

        self.cron_jobs = {
            "set_rtc": 60 * 60,  # Yes, the RTC sucks that bad.
            "set_timezones": 60 * 60 * 24,  # Daily, check for offset change
        }

    def set_timezones(self) -> list[timezone]:
        """Lookup all the current TZ offsets.

        Needs to be called to update when time zones change. (daily)"""

        self.status_label.text = "Time\nZones"
        self.timezones = [
            self.lookup_timezone(name=n, set_rtc=False) for n in self.timezone_names
        ]

    def set_rtc(self):
        self.status_label.text = "Time\nSync"
        self.lookup_timezone(name="UTC", set_rtc=True)

    def time_group(self) -> displayio.Group:
        group = displayio.Group(x=0, y=4)
        font_width, font_height = self.font.get_bounding_box()
        font_width -= 1
        line_height = 8
        now = datetime.now()
        for i, tz in enumerate(self.timezones):
            y = i * line_height
            tz_name = tz._name  # There's no property for this.
            country_code = COUNTRY_CODES[tz_name]
            flag_colors = FLAG_COLORS[country_code]
            print("Flag colors: {0} = {1}".format(tz_name, repr(flag_colors)))
            group.append(
                Label(
                    self.font,
                    text="{:2d}".format((now + tz.utcoffset(None)).hour),
                    color=self.color(flag_colors[0]),
                    x=0,
                    y=y,
                )
            )
            if i == 0:
                # First row has the actual minutes of the hour
                group.append(
                    Label(
                        self.font,
                        text=":",
                        color=self.color(flag_colors[1]),
                        x=font_width * 2,
                        y=y - 1,
                    )
                )
                group.append(
                    Label(
                        self.font,
                        text="{:02d}".format(now.minute),
                        color=self.color(flag_colors[2]),
                        x=font_width * 2 + 4,
                        y=y,
                    )
                )
            else:
                # Every other row, instead of the minutes, the country code is shown.
                group.append(
                    Label(
                        self.font,
                        text=country_code[0],
                        color=self.color(flag_colors[1]),
                        x=font_width * 2 + 4,
                        y=y,
                    )
                )
                group.append(
                    Label(
                        self.font,
                        text=country_code[1],
                        color=self.color(flag_colors[2]),
                        x=font_width * 3 + 5,
                        y=y,
                    )
                )
        return group

    def main(self) -> None:
        while True:
            print("Time: ", datetime.now())
            gc.collect()
            self.cron_run()
            self.display.root_group = self.time_group()

            time.sleep(10)


app = ZoneClock(TIMEZONES_to_SHOW)

if __name__ == "__main__":
    app.main()
