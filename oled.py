# Copyright 2026 Curtis Galloway
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SSD1306 monochrome OLED backend for the indicator firmware.

Loaded by code.py only when config.OLED is True. Handles the `oled ...`
commands. Drawing goes into the driver's RAM buffer and marks it dirty;
code.py calls `refresh()` once the incoming lines are drained, so a burst of
commands (clear + eight lines) costs one I2C transfer, not nine.

Needs on CIRCUITPY: lib/adafruit_ssd1306.mpy, lib/adafruit_framebuf.mpy and
font5x8.bin in the drive's root (the framebuf text font).
"""

import binascii

import adafruit_ssd1306
import board
import busio

# Built-in framebuf font: 5x8 glyphs on a 6-pixel pitch.
CHAR_W = 6
CHAR_H = 8

HELP = (
    "oled: clear | line <row> <text> | text <x> <y> <size> <text> | "
    "frame <base64> | invert <0|1> | contrast <0-255> | power <0|1> | info"
)


class Oled:
    """One SSD1306 on I2C."""

    def __init__(self, config):
        self.width = getattr(config, "OLED_WIDTH", 128)
        self.height = getattr(config, "OLED_HEIGHT", 64)
        sda = getattr(config, "OLED_SDA", None)
        scl = getattr(config, "OLED_SCL", None)
        if sda is not None and scl is not None:
            # 400 kHz: a full 1 KiB refresh takes ~25 ms instead of ~100 ms.
            i2c = busio.I2C(scl, sda, frequency=400000)
        else:
            i2c = board.STEMMA_I2C()
        addr = getattr(config, "OLED_ADDRESS", None)
        if addr is None:
            addr = self._find_address(i2c)
        self.addr = addr
        self.dev = adafruit_ssd1306.SSD1306_I2C(
            self.width, self.height, i2c, addr=addr
        )
        self.frame_len = self.width * self.height // 8
        self.dirty = False
        self.dev.fill(0)
        self.dev.text("ready", 0, 0, 1)
        self.dev.show()

    @staticmethod
    def _find_address(i2c):
        while not i2c.try_lock():
            pass
        try:
            found = i2c.scan()
        finally:
            i2c.unlock()
        for addr in (0x3C, 0x3D):
            if addr in found:
                return addr
        raise RuntimeError(
            "no SSD1306 at 0x3C or 0x3D; I2C devices: "
            + (", ".join(hex(a) for a in found) or "none")
        )

    def refresh(self):
        """Push the buffer to the panel if anything changed."""
        if self.dirty:
            self.dev.show()
            self.dirty = False

    # --- commands -----------------------------------------------------------

    def handle(self, arg):
        parts = arg.split(None, 1)
        if not parts:
            return HELP
        sub = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        if sub == "clear":
            self.dev.fill(0)
            self.dirty = True
            return "ok oled clear"
        if sub == "line":
            return self._line(rest)
        if sub == "text":
            return self._text(rest)
        if sub == "frame":
            return self._frame(rest)
        if sub == "invert":
            self.dev.invert(self._flag(rest))
            return "ok oled invert " + rest.strip()
        if sub == "contrast":
            v = int(rest)
            if not 0 <= v <= 255:
                raise ValueError("contrast must be 0..255")
            self.dev.contrast(v)
            return "ok oled contrast %d" % v
        if sub == "power":
            if self._flag(rest):
                self.dev.poweron()
            else:
                self.dev.poweroff()
            return "ok oled power " + rest.strip()
        if sub == "info":
            return "ok oled %dx%d addr 0x%02x cols %d rows %d" % (
                self.width,
                self.height,
                self.addr,
                self.width // CHAR_W,
                self.height // CHAR_H,
            )
        if sub == "help":
            return HELP
        raise ValueError("unknown oled command: " + sub)

    @staticmethod
    def _flag(s):
        s = s.strip()
        if s not in ("0", "1"):
            raise ValueError("expected 0 or 1")
        return s == "1"

    def _line(self, rest):
        # Text after the row number is kept verbatim, including leading
        # spaces, so a host can right-align or indent.
        row_s, _, text = rest.partition(" ")
        row = int(row_s)
        rows = self.height // CHAR_H
        if not 0 <= row < rows:
            raise ValueError("row must be 0..%d" % (rows - 1))
        y = row * CHAR_H
        self.dev.fill_rect(0, y, self.width, CHAR_H, 0)
        self.dev.text(text, 0, y, 1)
        self.dirty = True
        return "ok oled line %d" % row

    def _text(self, rest):
        parts = rest.split(" ", 3)
        if len(parts) < 4:
            raise ValueError("usage: oled text <x> <y> <size> <text>")
        x, y, size = int(parts[0]), int(parts[1]), int(parts[2])
        if not 1 <= size <= 8:
            raise ValueError("size must be 1..8")
        text = parts[3]
        # Clear the box behind the text so it can overwrite earlier text.
        self.dev.fill_rect(x, y, len(text) * CHAR_W * size, CHAR_H * size, 0)
        self.dev.text(text, x, y, 1, size=size)
        self.dirty = True
        return "ok oled text"

    def _frame(self, rest):
        data = binascii.a2b_base64(rest.strip())
        if len(data) != self.frame_len:
            raise ValueError(
                "frame must be %d bytes (got %d)" % (self.frame_len, len(data))
            )
        # The driver's buffer is in the panel's native page layout
        # (MONO_VLSB): byte = page*width + x, bit n = row page*8 + n.
        self.dev.buf[:] = data
        self.dirty = True
        return "ok oled frame"
