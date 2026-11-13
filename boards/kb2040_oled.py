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

"""config.py for an Adafruit KB2040 with a 128x64 SSD1306 OLED on STEMMA QT.

Copy this file to the CIRCUITPY drive *as* ``config.py``, along with
``oled.py`` and ``font5x8.bin``. Flash the ``adafruit_kb2040`` CircuitPython
build.

The OLED is driven by the `oled ...` commands. The onboard NeoPixel (GP17)
is the pixel display, so the alert commands still work on it; there is no
separate status light.
"""

import board

NUM_PIXELS = 1
DATA_PIN = board.NEOPIXEL
STATUS_PIN = None
POWER_PIN = None
PIXEL_ORDER = "GRB"

DEFAULT_COLOR = (255, 255, 255)
DEFAULT_BRIGHTNESS = 0.25

ELEMENTS = {"0": 0}

# --- OLED -------------------------------------------------------------------

OLED = True
OLED_WIDTH = 128
OLED_HEIGHT = 64
# The KB2040's STEMMA QT connector (GPIO 12/13). The adafruit_kb2040 build
# names these SDA/SCL (same objects as D12/D13); it has no GPnn names.
OLED_SDA = board.SDA
OLED_SCL = board.SCL
# None scans 0x3C then 0x3D. Adafruit's 0.96" board ships at 0x3D; its
# address jumper moves it to 0x3C.
OLED_ADDRESS = None
