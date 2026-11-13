<!--
Copyright 2026 Curtis Galloway

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# indicator — agent / developer notes

CircuitPython firmware that drives a string of NeoPixels back-lighting an
IEE-style **one-plane projection readout**, replacing the original incandescent
lamp module. A Waveshare **RP2040-Zero** runs it; a host commands it over USB
serial.

## How the hardware works

The readout projects a single film transparency that carries every glyph in a
grid. Back-lighting one cell projects one glyph onto the front screen. The
custom PCB drops a NeoPixel into each former lamp position, so **pixel N
illuminates cell N**. We treat the chain as a flat **framebuffer**: any set of
pixels can be lit at once, and a glyph is just an element (usually one pixel,
occasionally several) in that buffer.

- **MCU:** Waveshare RP2040-Zero. Onboard WS2812 is on **GP16** (used as a
  status light). External chain data defaults to **GP0** (`config.DATA_PIN`).
- **Power:** separate **5 V / 4 A** supply for the pixels — NOT off USB. Tie the
  pixel supply ground to the RP2040 ground; the 3.3 V data line is only valid
  against a shared reference.
- **Level shifting:** RP2040 drives 3.3 V data into 5 V pixels. Often works for
  short runs; if the first pixel is flaky, add a 74AHCT125 / SN74LVC1T45 on the
  data line. (Open question — confirm what the PCB does.)

## Files

| File | Role |
|------|------|
| `boot.py` | Enables the second USB CDC (data) port. **Power-cycle** after copying — soft reset does not re-run it. |
| `code.py` | Framebuffer + line protocol + calibration + status LED. |
| `config.py` | The only file you edit per board: `NUM_PIXELS`, pins, defaults, and the `ELEMENTS` map. |
| `boards/*.py` | Ready-made `config.py` for other boards; copy one to the drive *as* `config.py`. |
| `oled.py` | SSD1306 OLED backend, loaded only when `config.OLED` is true. Handles `oled ...`. Needs `font5x8.bin` in the drive root (from the Adafruit_CircuitPython_framebuf examples). |
| `host/indicator.py` | Host CLI to send commands / auto-detect the data port, plus `write` and `image` for OLED boards. A uv script (PEP 723 header lists pyserial and Pillow; shebang `uv run --script`), so it runs directly or symlinked as `~/.local/bin/indicator`. |
| `case/monitor_case.scad` | 3D-printable monitor-top case for the bare RP2040-Zero (opaque clip + translucent cover). See `case/README.md`. |

## Boards

| Board | Config | Notes |
|-------|--------|-------|
| Waveshare RP2040-Zero | `config.py` | External chain on GP0, onboard GP16 pixel as status light. |
| RP2040-Zero, bare (alert light) | `boards/rp2040_zero_alert.py` | No external chain: the onboard GP16 pixel is the whole display, so there is no status light. Flash the `waveshare_rp2040_zero` CircuitPython build. |
| Adafruit KB2040 + 128x64 SSD1306 OLED | `boards/kb2040_oled.py` | OLED on the STEMMA QT port (I2C, GPIO 12/13 at 400 kHz; the `adafruit_kb2040` build calls them `board.SDA`/`board.SCL` and has no `GPnn` names). Address auto-detected (0x3C or 0x3D; the tested panel answered at 0x3D). Onboard NeoPixel is the pixel display, so alerts work on it; no status light. Extra libraries: `adafruit_ssd1306`, `adafruit_framebuf`. |

**Identify the board from its silkscreen, never from `boot_out.txt`.** That
file names the CircuitPython build that was flashed, not the hardware. A
build for the wrong board runs fine and answers every command while driving
the wrong pins, so nothing lights. On 2026-10-29 an RP2040-Zero was mistaken
for a XIAO RP2040 this way.

## Deploying to the board

1. Install CircuitPython on the RP2040-Zero (drag the UF2 while in bootloader).
2. Add the NeoPixel library: `circup install neopixel`
   (pulls in `neopixel.mpy` + `adafruit_pixelbuf` to `CIRCUITPY/lib/`).
3. Copy `boot.py`, `code.py`, `config.py` to the `CIRCUITPY` drive.
4. **Power-cycle** so `boot.py` enables the data port.

For the KB2040 OLED board, also copy `oled.py` and `font5x8.bin` to the drive
root and `circup install adafruit_ssd1306` (pulls in `adafruit_framebuf`).

## Serial protocol (one command per line, on the DATA port)

| Command | Effect |
|---------|--------|
| `show <expr>` | Light the union of `+`-joined elements with replace-semantics, e.g. `show 5`, `show A+B+C`. |
| `blank` / `clear` / `off` | All pixels off. |
| `px <i[,j,...]> [hex]` | Set raw pixel indices to a color, **additively** (no clear). |
| `color <hex>` | Set the active lit color (`ff8800`). |
| `bright <0-100>` | Brightness percent. |
| `cal` | Interactive calibration (see below). |
| `alert <level>` | Latch an alert: `warning`, `caution` or `advisory`. Replies `ok alerts <active,...>`. |
| `ack [level]` | Clear one latched alert, or all with no argument. |
| `alerts` | Report latched alerts, most urgent first, or `ok alerts none`. |
| `ping` | Replies `ok pong` (used by `--auto` port detection). |
| `oled clear` | Blank the OLED. |
| `oled line <row> <text>` | Replace text row 0–7 (21 columns of the 5x8 font); text after the row is kept verbatim. |
| `oled text <x> <y> <size> <text>` | Draw text at pixel x,y, scaled 1–8, clearing the box behind it. |
| `oled frame <base64>` | Replace the whole screen: 1024 bytes in the panel's page layout (byte `page*128 + x`, bit n = row `page*8 + n`). The host's `image` command builds this. |
| `oled invert <0\|1>` / `oled contrast <0-255>` / `oled power <0\|1>` | Panel settings. |
| `oled info` | Replies size, I2C address, and text columns/rows. |
| `help` | List commands. |

Replies are prefixed `ok`, `err `, or `cal` so a host can parse outcomes.
Messages the board sends on its own (the boot banner, an OLED being disabled)
start with `note `; the host CLI skips them when reading a reply.
Lines longer than 2048 bytes are discarded with `err line too long` (the
limit is sized for `oled frame`).

OLED drawing goes to a RAM buffer; the panel is refreshed once the incoming
commands are drained, so a burst (clear plus eight lines) costs one I2C
transfer. The OLED commands are not affected by latched alerts.

## Alerts

Alerts latch until acknowledged; nothing expires on its own, and with nothing
latched the alert layer is dark. The whole chain shows the most urgent latched
level. Each level differs in rhythm as well as color, so they can be told apart
without relying on color:

| Level | Color | Rhythm |
|-------|-------|--------|
| `warning` | white | 4 Hz strobe |
| `caution` | yellow | double blink every 1.5 s |
| `advisory` | blue | slow 4 s fade in and out |

The palette stays distinct under red-green color blindness, where red and
amber can both read as green. White, yellow and blue stay distinct. They also
have equal red and green, so they look the same whether a pixel is wired GRB
or RGB. Red would bring back that wiring question, which a red-green
colorblind viewer cannot settle by eye.

While any alert is latched, the framebuffer commands (`show`, `blank`/`clear`/
`off`, `px`, `bright`, `cal`) reply `err alert latched`. The last `ack`
restores whatever the chain showed before the first alert.

## Host CLI exit status

`host/indicator.py` with a one-shot command exits: `0` ok; `1` the board said
`ok alerts none` (nothing latched — use `|| true` under `set -e`); `2` the board
replied `err`; `3` no board found (or pyserial missing); `22` no reply, so the
outcome is unknown — check with `alerts` before retrying.

## Calibration — build the `ELEMENTS` map

Mapping pixel index → glyph depends on PCB routing, so discover it by looking at
the screen:

1. Send `cal`. Pixel 0 lights.
2. Type the label that projects (`5`, `A`, …). Or `skip`, `back`, `done`,
   `abort`.
3. Repeat to the end (or `done`). It prints a ready-to-paste
   `ELEMENTS = {…}` and applies it live so you can test immediately.
4. Paste that into `config.py` so it survives reboot.

`ELEMENTS` values may be a single index or a tuple of indices (a label that
lights several LEDs). `show` unions them.

## Conventions

- Apache-2.0 headers on every source/instruction file.
- `config.py` holds all per-board values; keep `code.py` board-agnostic.
- Multi-digit / multi-module is future work but already accommodated: chaining
  more modules just makes `NUM_PIXELS` larger and the `ELEMENTS` map longer.
