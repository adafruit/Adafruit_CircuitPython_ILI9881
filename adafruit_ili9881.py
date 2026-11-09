# SPDX-FileCopyrightText: Copyright (C) 2017-2018 Bootlin
# SPDX-FileCopyrightText: Copyright (C) 2021 Henson Li and Penk Chen
# SPDX-FileCopyrightText: Copyright (C) 2022 Mark Williams
# SPDX-FileCopyrightText: Copyright (c) 2022 Raspberry Pi Ltd.
# SPDX-FileCopyrightText: Copyright (c) 2026 Adafruit Industries
#
# SPDX-License-Identifier: GPL-2.0-only
"""
`adafruit_ili9881`
================================================================================

CircuitPython driver for the ILI9881 MIPI DSI display panels


* Author(s): Liz Clark, ladyada, Mark Williams, Henson Li, Penk Chen

Implementation Notes
--------------------

* Register sequence from the Raspberry Pi Linux panel-ilitek-ili9881c driver:
* Copyright (C) 2017-2018 Bootlin; 2021 Henson Li and Penk Chen;
* 2022 Mark Williams. MCU protocol: Copyright (C) 2022 Raspberry Pi Ltd.
* https://github.com/raspberrypi/linux/blob/rpi-6.12.y/drivers/gpu/drm/panel/panel-ilitek-ili9881c.c
* Adapted for CircuitPython

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import time

import digitalio
import mipidsi
from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import Any

    import busio
    from microcontroller import Pin
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ILI9881.git"

_BUS_FREQUENCY_TOLERANCE = const(1_000)

# Initialization sequences, in mipidsi.Display's format: command, data length
# (bit 7 set adds a delay), data, and the delay in milliseconds if any. Each
# ends by switching to command page 0, enabling the tearing signal, leaving
# sleep mode, waiting 120 ms and turning the display on
_INIT_RPI_7INCH = bytes.fromhex(
    "ff 03 98 81 03 01 01 00 02 01 00 03 01 73 04 01 00 05 01 00 06 01 0a 07"
    "01 00 08 01 00 09 01 61 0a 01 00 0b 01 00 0c 01 01 0d 01 00 0e 01 00 0f"
    "01 61 10 01 61 11 01 00 12 01 00 13 01 00 14 01 00 15 01 00 16 01 00 17"
    "01 00 18 01 00 19 01 00 1a 01 00 1b 01 00 1c 01 00 1d 01 00 1e 01 40 1f"
    "01 80 20 01 06 21 01 01 22 01 00 23 01 00 24 01 00 25 01 00 26 01 00 27"
    "01 00 28 01 33 29 01 03 2a 01 00 2b 01 00 2c 01 00 2d 01 00 2e 01 00 2f"
    "01 00 30 01 00 31 01 00 32 01 00 33 01 00 34 01 04 35 01 00 36 01 00 37"
    "01 00 38 01 3c 39 01 00 3a 01 00 3b 01 00 3c 01 00 3d 01 00 3e 01 00 3f"
    "01 00 40 01 00 41 01 00 42 01 00 43 01 00 44 01 00 50 01 10 51 01 32 52"
    "01 54 53 01 76 54 01 98 55 01 ba 56 01 10 57 01 32 58 01 54 59 01 76 5a"
    "01 98 5b 01 ba 5c 01 dc 5d 01 fe 5e 01 00 5f 01 0e 60 01 0f 61 01 0c 62"
    "01 0d 63 01 06 64 01 07 65 01 02 66 01 02 67 01 02 68 01 02 69 01 01 6a"
    "01 00 6b 01 02 6c 01 15 6d 01 14 6e 01 02 6f 01 02 70 01 02 71 01 02 72"
    "01 02 73 01 02 74 01 02 75 01 0e 76 01 0f 77 01 0c 78 01 0d 79 01 06 7a"
    "01 07 7b 01 02 7c 01 02 7d 01 02 7e 01 02 7f 01 01 80 01 00 81 01 02 82"
    "01 14 83 01 15 84 01 02 85 01 02 86 01 02 87 01 02 88 01 02 89 01 02 8a"
    "01 02 ff 03 98 81 04 6c 01 15 6e 01 2a 6f 01 33 3b 01 98 3a 01 94 8d 01"
    "14 87 01 ba 26 01 76 b2 01 d1 b5 01 06 38 01 01 39 01 00 ff 03 98 81 01"
    "22 01 0a 31 01 00 53 01 7d 55 01 8f 40 01 33 50 01 96 51 01 96 60 01 23"
    "a0 01 08 a1 01 1d a2 01 2a a3 01 10 a4 01 15 a5 01 28 a6 01 1c a7 01 1d"
    "a8 01 7e a9 01 1d aa 01 29 ab 01 6b ac 01 1a ad 01 18 ae 01 4b af 01 20"
    "b0 01 27 b1 01 50 b2 01 64 b3 01 39 c0 01 08 c1 01 1d c2 01 2a c3 01 10"
    "c4 01 15 c5 01 28 c6 01 1c c7 01 1d c8 01 7e c9 01 1d ca 01 29 cb 01 6b"
    "cc 01 1a cd 01 18 ce 01 4b cf 01 20 d0 01 27 d1 01 50 d2 01 64 d3 01 39"
    "ff 03 98 81 00 35 01 00 11 80 78 29 00"
)

_INIT_RPI_5INCH = bytes.fromhex(
    "ff 03 98 81 03 01 01 00 02 01 00 03 01 73 04 01 73 05 01 00 06 01 06 07"
    "01 02 08 01 00 09 01 01 0a 01 01 0b 01 01 0c 01 01 0d 01 01 0e 01 01 0f"
    "01 01 10 01 01 11 01 00 12 01 00 13 01 01 14 01 00 15 01 00 16 01 00 17"
    "01 00 18 01 00 19 01 00 1a 01 00 1b 01 00 1c 01 00 1d 01 00 1e 01 c0 1f"
    "01 80 20 01 04 21 01 03 22 01 00 23 01 00 24 01 00 25 01 00 26 01 00 27"
    "01 00 28 01 33 29 01 03 2a 01 00 2b 01 00 2c 01 00 2d 01 00 2e 01 00 2f"
    "01 00 30 01 00 31 01 00 32 01 00 33 01 00 34 01 03 35 01 00 36 01 03 37"
    "01 00 38 01 00 39 01 00 3a 01 00 3b 01 00 3c 01 00 3d 01 00 3e 01 00 3f"
    "01 00 40 01 00 41 01 00 42 01 00 43 01 00 44 01 00 50 01 01 51 01 23 52"
    "01 45 53 01 67 54 01 89 55 01 ab 56 01 01 57 01 23 58 01 45 59 01 67 5a"
    "01 89 5b 01 ab 5c 01 cd 5d 01 ef 5e 01 10 5f 01 09 60 01 08 61 01 0f 62"
    "01 0e 63 01 0d 64 01 0c 65 01 02 66 01 02 67 01 02 68 01 02 69 01 02 6a"
    "01 02 6b 01 02 6c 01 02 6d 01 02 6e 01 02 6f 01 02 70 01 02 71 01 06 72"
    "01 07 73 01 02 74 01 02 75 01 06 76 01 07 77 01 0e 78 01 0f 79 01 0c 7a"
    "01 0d 7b 01 02 7c 01 02 7d 01 02 7e 01 02 7f 01 02 80 01 02 81 01 02 82"
    "01 02 83 01 02 84 01 02 85 01 02 86 01 02 87 01 09 88 01 08 89 01 02 8a"
    "01 02 ff 03 98 81 04 6c 01 15 6e 01 2a 6f 01 57 3a 01 a4 8d 01 1a 87 01"
    "ba 26 01 76 b2 01 d1 ff 03 98 81 01 22 01 0a 31 01 00 53 01 35 55 01 50"
    "50 01 af 51 01 af 60 01 14 a0 01 08 a1 01 1d a2 01 2c a3 01 14 a4 01 19"
    "a5 01 2e a6 01 22 a7 01 23 a8 01 97 a9 01 1e aa 01 29 ab 01 7b ac 01 18"
    "ad 01 17 ae 01 4b af 01 1f b0 01 27 b1 01 52 b2 01 63 b3 01 39 c0 01 08"
    "c1 01 1d c2 01 2c c3 01 14 c4 01 19 c5 01 2e c6 01 22 c7 01 23 c8 01 97"
    "c9 01 1e ca 01 29 cb 01 7b cc 01 18 cd 01 17 ce 01 4b cf 01 1f d0 01 27"
    "d1 01 52 d2 01 63 d3 01 39 ff 03 98 81 00 35 01 00 11 80 78 29 00"
)

# Raspberry Pi Touch Display 2 controller registers
_CONTROLLER_ADDRESS = const(0x45)
_REG_ID = const(0x01)
_REG_POWERON = const(0x02)
_REG_PWM = const(0x03)
_LCD_RESET_BIT = const(0x01)
_CTP_RESET_BIT = const(0x02)
_PWM_BL_ENABLE = const(0x80)
_MAX_BRIGHTNESS = const(31)

_RPI_TIMING = {
    "width": 720,
    "height": 1280,
    "hsync_pulse_width": 33,
    "hsync_back_porch": 50,
    "hsync_front_porch": 239,
    "vsync_pulse_width": 2,
    "vsync_back_porch": 30,
    "vsync_front_porch": 20,
    "pixel_clock_frequency": 83_330_000,
}

# panel size in inches, initialization sequence and timing
_PANELS_BY_ID = {
    0x01: (7, _INIT_RPI_7INCH, _RPI_TIMING),
    0x04: (7, _INIT_RPI_7INCH, _RPI_TIMING),  # older 7-inch
    0x08: (5, _INIT_RPI_5INCH, _RPI_TIMING),  # older 5-inch
    0x09: (5, _INIT_RPI_5INCH, _RPI_TIMING),
}


class ILI9881(mipidsi.Display):
    """ILI9881C MIPI DSI display panel.

    Resets the panel if a reset pin is given, sends its initialization
    sequence and starts DSI video. The panel must already be powered. Use it
    with `framebufferio.FramebufferDisplay` like any other ``mipidsi.Display``.

    :param ~mipidsi.Bus bus: DSI bus connected to the panel. Create it with a
        ``minimum_frequency`` of at least ``color_depth`` times the pixel clock
        divided by the number of lanes. The panel checks the rate the bus
        actually runs at, which can be higher.
    :param bytes init_sequence: Commands sent to the panel after reset, in
        ``mipidsi.Display``'s format
    :param int width: Active horizontal pixels, in the panel's native
        orientation
    :param int height: Active vertical lines, in the panel's native orientation
    :param int hsync_pulse_width: Horizontal sync width in pixels
    :param int hsync_back_porch: Horizontal back porch in pixels
    :param int hsync_front_porch: Horizontal front porch in pixels
    :param int vsync_pulse_width: Vertical sync width in lines
    :param int vsync_back_porch: Vertical back porch in lines
    :param int vsync_front_porch: Vertical front porch in lines
    :param int pixel_clock_frequency: Pixel clock in Hz
    :param int color_depth: 24 (RGB888) or 16 (RGB565). Live video with
        `videocore` needs 16, with ``rotation=0`` on the
        `framebufferio.FramebufferDisplay`, because video frames are copied to
        the screen as-is.
    :param ~microcontroller.Pin reset: Optional active-low reset pin. Leave it
        out when something else resets the panel, as on the Raspberry Pi
        Touch Display 2.
    :param kwargs: Other ``mipidsi.Display`` arguments
    :raises ValueError: If the bus is too slow for the pixel clock
    """

    def __init__(  # noqa: PLR0913
        self,
        bus: mipidsi.Bus,
        init_sequence: bytes,
        *,
        width: int,
        height: int,
        hsync_pulse_width: int,
        hsync_back_porch: int,
        hsync_front_porch: int,
        vsync_pulse_width: int,
        vsync_back_porch: int,
        vsync_front_porch: int,
        pixel_clock_frequency: int,
        color_depth: int = 24,
        reset: Pin | None = None,
        **kwargs: Any,
    ) -> None:
        self._reset_pin = None
        if reset is not None:
            # Same pulse as the Linux driver: 20 ms in reset, 20 ms to start.
            self._reset_pin = digitalio.DigitalInOut(reset)
            self._reset_pin.switch_to_output(value=False)
            time.sleep(0.02)
            self._reset_pin.value = True
            time.sleep(0.02)

        super().__init__(
            bus,
            init_sequence,
            width=width,
            height=height,
            hsync_pulse_width=hsync_pulse_width,
            hsync_back_porch=hsync_back_porch,
            hsync_front_porch=hsync_front_porch,
            vsync_pulse_width=vsync_pulse_width,
            vsync_back_porch=vsync_back_porch,
            vsync_front_porch=vsync_front_porch,
            pixel_clock_frequency=pixel_clock_frequency,
            color_depth=color_depth,
            **kwargs,
        )

        needed = (self.pixel_clock_frequency * color_depth + bus.num_lanes - 1) // bus.num_lanes
        if bus.frequency + _BUS_FREQUENCY_TOLERANCE < needed:
            self.deinit()
            raise ValueError(
                f"bus runs at {bus.frequency}, below the {needed} needed for this pixel clock"
            )

    def deinit(self) -> None:
        """Stop the display and release the reset pin."""
        if self._reset_pin is not None:
            self._reset_pin.deinit()
            self._reset_pin = None
        super().deinit()


class RaspberryPiTouchDisplay2(ILI9881):
    """Raspberry Pi Touch Display 2, 5-inch or 7-inch, detected automatically.

    The display's controller (at I2C address 0x45) powers and resets the
    panel and the touch controller and drives the backlight. This resets
    both, releases them, then initializes the panel. Use it with
    `framebufferio.FramebufferDisplay`: ``rotation=90`` gives 1280 x 720
    landscape.

    :param ~mipidsi.Bus bus: DSI bus connected to the display. Create it with
        ``minimum_frequency=RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY``
        and ``num_lanes=2``.
    :param ~busio.I2C i2c: I2C bus on the display connector
    :param int color_depth: 24 (RGB888) or 16 (RGB565)
    :param int brightness: Backlight brightness, 0 to 31
    :param kwargs: Other ``mipidsi.Display`` arguments
    :raises RuntimeError: If no 5-inch or 7-inch Touch Display 2 answers
    :raises ValueError: If the bus is too slow for the pixel clock
    """

    MINIMUM_BUS_FREQUENCY = 1_000_000_000
    """Bus rate both panels need at 24-bit color over 2 lanes"""

    def __init__(
        self,
        bus: mipidsi.Bus,
        i2c: busio.I2C,
        *,
        color_depth: int = 24,
        brightness: int = 8,
        **kwargs: Any,
    ) -> None:
        if not 0 <= brightness <= _MAX_BRIGHTNESS:
            raise ValueError(f"brightness must be 0 to {_MAX_BRIGHTNESS}")
        self._controller = I2CDevice(i2c, _CONTROLLER_ADDRESS)
        identity = self._read_id() & 0x0F
        if identity not in _PANELS_BY_ID:
            raise RuntimeError("No Raspberry Pi Touch Display 2 (5-inch or 7-inch) found")
        self.size, init_sequence, timing = _PANELS_BY_ID[identity]
        """The panel size in inches, 5 or 7"""

        self._write(_REG_PWM, 0)
        self._write(_REG_POWERON, 0)
        time.sleep(0.02)
        self._write(_REG_POWERON, _LCD_RESET_BIT | _CTP_RESET_BIT)
        time.sleep(0.02)

        super().__init__(bus, init_sequence, color_depth=color_depth, **timing, **kwargs)

        self._brightness = 0
        self.brightness = brightness

    def deinit(self) -> None:
        """Turn off the backlight, hold the panel and touch controller in
        reset, and stop the display."""
        try:
            self._write(_REG_PWM, 0)
            self._write(_REG_POWERON, 0)
        except OSError:
            pass  # the display may already be disconnected
        super().deinit()

    def _read_id(self) -> int:
        identity = bytearray(1)
        with self._controller as controller:
            controller.write(bytes((_REG_ID,)))
            time.sleep(0.005)
            controller.readinto(identity)
        return identity[0]

    def _write(self, register: int, value: int) -> None:
        with self._controller as controller:
            controller.write(bytes((register, value)))

    @property
    def brightness(self) -> int:
        """Backlight brightness, 0 (off) to 31 (brightest)"""
        return self._brightness

    @brightness.setter
    def brightness(self, value: int) -> None:
        if not 0 <= value <= _MAX_BRIGHTNESS:
            raise ValueError(f"brightness must be 0 to {_MAX_BRIGHTNESS}")
        self._brightness = value
        self._write(_REG_PWM, (_PWM_BL_ENABLE | value) if value else 0)
