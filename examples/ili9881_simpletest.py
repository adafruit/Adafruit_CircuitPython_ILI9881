# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Color bars on a Raspberry Pi Touch Display 2 (5-inch or 7-inch)."""

import bitmaptools
import board
import displayio
import framebufferio
import mipidsi

import adafruit_ili9881

displayio.release_displays()

bus = mipidsi.Bus(
    minimum_frequency=adafruit_ili9881.RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY,
    num_lanes=2,
)
panel = adafruit_ili9881.RaspberryPiTouchDisplay2(bus, board.I2C())
display = framebufferio.FramebufferDisplay(panel, rotation=90)
print(f"{panel.size}-inch display, {display.width} x {display.height}")

# colors: white, yellow, cyan, green, magenta, red, blue, black
palette = displayio.Palette(8)
for index, color in enumerate(
    (0xFFFFFF, 0xFFFF00, 0x00FFFF, 0x00FF00, 0xFF00FF, 0xFF0000, 0x0000FF, 0x000000)
):
    palette[index] = color

bar_width = display.width // 8
bitmap = displayio.Bitmap(display.width, display.height, 8)
for index in range(8):
    bitmaptools.fill_region(
        bitmap, index * bar_width, 0, (index + 1) * bar_width, display.height, index
    )

bars = displayio.Group()
bars.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = bars

while True:
    pass
