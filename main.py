# pyright: reportShadowedImports=false
# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Ash's multi-TZ wall clock
"""

import gc
import time
import math
import displayio
import terminalio
from adafruit_datetime import datetime
from adafruit_display_text.label import Label
from adafruit_matrixportal.matrix import Matrix

import colors2 as colors
from networking import network_setup, network_test, lookup_timezone

MATRIX = Matrix(bit_depth=6, width=32, height=32)
# DISPLAY: framebufferio.FramebufferDisplay = MATRIX.display
# DISPLAY.brightness = 0.2
DISPLAY = MATRIX.display
DISPLAY.brightness = 0.2
NETWORK: ESPSPI_WiFiManager = None

TIMEZONE_NAMES = [
    "America/Los_Angeles",
    "Europe/Berlin",
    "Europe/Athens",
    "Asia/Kuala_Lumpur",
]
COUNTRY_CODES = ["US", "DE", "GR", "MY"]
TIMEZONES = []
COLORS = [
    [colors.RED, colors.WHITE, colors.BLUE],
    [colors.GRAY, colors.RED, colors.GOLD],
    [colors.BLUE, colors.WHITE, colors.BLUE],
    [colors.YELLOW, colors.BLUE, colors.RED],
]
FONT = terminalio.FONT
# SMALL_FONT = bitmap_font.load_font("/fonts/helvR10.bdf")
# SMALL_FONT.load_glyphs("0123456789:/.%")
# print("Fonts loaded")
LINE_SPACING = 0.75
GROUP: displayio.Group = displayio.Group(x=2, y=0)
GROUP.append(
    Label(
        FONT, text="Booting", color=colors.ORCHID, x=0, y=10, line_spacing=LINE_SPACING
    )
)
DISPLAY.root_group = GROUP


def init() -> None:
    global NETWORK, GROUP, TIMEZONES

    GROUP[0].color = colors.PURPLE
    GROUP[0].text = "WiFi\nSetup"
    # DISPLAY.show()
    NETWORK = network_setup()
    network_test(requests=NETWORK)
    GROUP[0].text = "Time\nSync"
    # DISPLAY.show()
    lookup_timezone(requests=NETWORK, name="UTC", set_rtc=True)
    GROUP[0].text = "Time\nZones"
    TIMEZONES = [
        lookup_timezone(requests=NETWORK, name=tz, set_rtc=False)
        for tz in TIMEZONE_NAMES
    ]


def display_group() -> displayio.Group:
    group = displayio.Group(x=0, y=4)
    font_width, font_height = FONT.get_bounding_box()
    font_width -= 1
    line_height = 8
    now = datetime.now()
    for i in range(len(TIMEZONES)):
        y = i * line_height
        group.append(
            Label(
                FONT,
                text="{:2d}".format((now + TIMEZONES[i].utcoffset(None)).hour),
                color=COLORS[i][0],
                x=0,
                y=y,
            )
        )
        if i == 0:
            group.append(
                Label(
                    FONT,
                    text=":",
                    color=COLORS[i][1],
                    x=font_width * 2,
                    y=y - 1,
                )
            )
            group.append(
                Label(
                    FONT,
                    text="{:02d}".format(now.minute),
                    color=COLORS[i][2],
                    x=font_width * 2 + 4,
                    y=y,
                )
            )
        else:
            group.append(
                Label(
                    FONT,
                    text=COUNTRY_CODES[i][0],
                    color=COLORS[i][1],
                    x=font_width * 2 + 4,
                    y=y,
                )
            )
            group.append(
                Label(
                    FONT,
                    text=COUNTRY_CODES[i][1],
                    color=COLORS[i][2],
                    x=font_width * 3 + 5,
                    y=y,
                )
            )
    return group


def main() -> None:
    init()

    # GROUP: displayio.Group = display_group()

    while True:
        print("Time: ", datetime.now())
        gc.collect()
        DISPLAY.root_group = display_group()
        # DISPLAY.refresh()
        # DISPLAY.auto_brightness = True
        # DISPLAY.show()
        time.sleep(10)


if __name__ == "__main__":
    main()
