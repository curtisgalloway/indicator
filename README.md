# indicator

Drive an **IEE-style one-plane projection readout** with a string of NeoPixels
instead of its original incandescent lamp module, controlled by a Waveshare
**RP2040-Zero** running CircuitPython. A host sends one-line commands over USB
serial; the RP2040 lights the right pixel(s), back-projecting the glyph through
the installed transparency.

The pixel chain is a flat framebuffer, so you can light **multiple LEDs at
once** — a glyph is usually one pixel, but a composed image can be several
(`show A+B+C`).

## Quick start

The host CLI, `host/indicator.py`, is a self-contained
[uv](https://docs.astral.sh/uv/) script: it declares its own dependencies, so
it runs directly once [uv](https://docs.astral.sh/uv/) is installed. Put it on
your PATH once:

```sh
ln -s "$PWD/host/indicator.py" ~/.local/bin/indicator
```

The first run takes a second while uv fetches pyserial and Pillow into a cache.

1. Flash CircuitPython onto the RP2040-Zero.
2. `circup install neopixel`
3. Copy `boot.py`, `code.py`, `config.py` to the `CIRCUITPY` drive.
4. **Power-cycle the board** (so `boot.py` enables the data serial port).
5. Calibrate, then drive it:

```sh
indicator --auto cal     # walk the chain, map glyphs
indicator --auto show 5  # project a glyph
indicator --auto blank   # clear
```

Paste the `ELEMENTS = {…}` line that `cal` prints into `config.py` so the map
survives a reboot.

## Alert light (bare RP2040-Zero)

The same firmware turns a bare RP2040-Zero's onboard pixel into a latched alert
light. Install as above, but copy `boards/rp2040_zero_alert.py` to the drive as
`config.py`. Then:

```sh
indicator --auto alert warning   # white strobe
indicator --auto alert caution   # yellow double blink
indicator --auto alert advisory  # blue slow fade
indicator --auto alerts          # what is latched
indicator --auto ack             # clear all, go dark
```

The most urgent latched alert is shown; alerts stay on until acknowledged.

## Text and image display (KB2040 + OLED)

The same firmware drives a 128x64 SSD1306 OLED plugged into an Adafruit
KB2040's STEMMA QT port. Flash the `adafruit_kb2040` CircuitPython build,
`circup install neopixel adafruit_ssd1306`, then copy `boot.py`, `code.py`,
`oled.py` and `font5x8.bin` to the drive and `boards/kb2040_oled.py` as
`config.py`, and power-cycle. Then:

```sh
indicator --auto write "first line" "second line"
uptime | indicator --auto write -
indicator --auto image photo.png
indicator --auto oled text 0 24 2 BIG
indicator --auto oled clear
```

`write` clears the screen and shows up to 8 lines of 21 characters. `image`
scales any picture to fit, dithers it to black and white (`--threshold N` for
a hard cutoff, `--invert` to swap), and sends it as one frame.

## Wiring

- Pixel data ← `config.DATA_PIN` (default **GP0**). Onboard GP16 pixel is the
  status light.
- Pixels powered from a separate **5 V / 4 A** supply; **common ground** with
  the RP2040.

See [`AGENTS.md`](AGENTS.md) for the full protocol, calibration details, and
hardware notes.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
