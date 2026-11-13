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

"""config.py for a bare RP2040-Zero used as a one-pixel alert light.

Copy this file to the CIRCUITPY drive *as* ``config.py``. With no external
chain attached, the onboard WS2812 (GP16) is the whole display, so it cannot
double as the status light.
"""

import board

NUM_PIXELS = 1
DATA_PIN = board.NEOPIXEL
STATUS_PIN = None
POWER_PIN = None
PIXEL_ORDER = "GRB"

DEFAULT_COLOR = (255, 255, 255)

# The pixel sits close to your eyes on a desk; full scale is glaring.
DEFAULT_BRIGHTNESS = 0.25

ELEMENTS = {"0": 0}
