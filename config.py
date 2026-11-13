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

"""User-editable configuration for the NeoPixel readout module.

This is the only file you should normally need to touch per board/build. The
ELEMENTS map is the heart of it: run `cal` over USB serial to discover it, then
paste the result here so it survives a reboot.
"""

import board

# --- Hardware ---------------------------------------------------------------

# Number of NeoPixels in the chain (across all chained modules). Calibration
# does not depend on this being exact -- if it is wrong you will see it
# immediately and just change this one line.
NUM_PIXELS = 12

# GPIO driving the external NeoPixel chain's DIN. Set this to whatever your
# PCB wires the data line to. (The RP2040-Zero's ONBOARD pixel is GP16; we use
# that for status, below, so pick a different pin here.)
DATA_PIN = board.GP0

# Onboard WS2812 on the Waveshare RP2040-Zero (GP16), used as a status light.
# Falls back gracefully if the board does not expose a NEOPIXEL alias. Set to
# None on a board whose only pixel IS the display (see boards/).
STATUS_PIN = getattr(board, "NEOPIXEL", None) or board.GP16

# Pin that must be driven high before the pixels get power, or None. The
# RP2040-Zero powers its pixels unconditionally.
POWER_PIN = None

# Color order of your pixels. WS2812/WS2812B are "GRB"; some SK6812 are "GRBW".
PIXEL_ORDER = "GRB"

# --- Display defaults -------------------------------------------------------

# Default lit color. White (equal R=G=B) is the natural choice for projecting a
# transparency; change it to project colored glyphs.
DEFAULT_COLOR = (255, 255, 255)

# Default brightness, 0.0-1.0. Capped below full so a multi-element symbol on a
# long chain stays within a sane current draw and the projection isn't blinding.
DEFAULT_BRIGHTNESS = 0.4

# --- Element map ------------------------------------------------------------

# label -> pixel index, OR label -> (tuple/list of pixel indices) for a label
# that lights more than one LED. `show` unions the pixels of every "+"-joined
# label. Matching is case-insensitive.
#
# This default is a PLACEHOLDER identity map for a 12-cell module. Run `cal`,
# observe what each pixel projects, and replace this with the real mapping.
ELEMENTS = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "11": 11,
}
