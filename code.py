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

"""NeoPixel readout firmware for a Waveshare RP2040-Zero (CircuitPython).

Drives a string of NeoPixels that back-light the transparency of an IEE-style
one-plane projection readout, replacing the original incandescent lamp module.
The chain is treated as a flat framebuffer so any number of pixels can be lit
at once; a `show` expression unions named ELEMENTS with `+`.

Talk to it over the USB *data* serial port (see boot.py), one command per line.

Commands (newline-terminated):
    show <expr>     light the union of elements, e.g.  show 5   or  show A+B+C
    blank           all pixels off  (aliases: clear, off)
    px <i[,j]> [hex] set raw pixel indices to a color, additively (no clear)
    color <hex>     set the active lit color, e.g.  color ff8800
    bright <0-100>  set brightness percent
    cal             interactive calibration: walks the chain, prints the map
    alert <level>   latch an alert: warning | caution | advisory
    ack [level]     clear one latched alert, or all of them
    alerts          -> "ok alerts warning,caution"  or  "ok alerts none"
    ping            -> "ok pong"   (handy for host port auto-detect)
    oled <sub> ...  draw on an SSD1306 OLED, when config.OLED is set
                    (see oled.py; `oled help` lists the subcommands)
    help            list commands

Replies start with "ok", "err ", or "cal" so a host can parse outcomes.

While any alert is latched, the whole chain shows the most urgent one's
pattern and the framebuffer commands are refused; the last `ack` restores
whatever was showing before. Each level has its own rhythm as well as its own
color, so the levels can be told apart without relying on color.
"""

import time

import board  # noqa: F401  (kept for parity with config / future use)
import digitalio
import neopixel
import usb_cdc

import config

HELP = (
    "commands: show <expr> | blank | px <i,j> [hex] | color <hex> | "
    "bright <0-100> | cal | alert <level> | ack [level] | alerts | ping | "
    "oled <sub> | help"
)

# Most urgent first; the first latched level in this order is the one shown.
ALERT_LEVELS = ("warning", "caution", "advisory")
# White, yellow and blue stay distinct under red-green color blindness, and
# each has equal red and green, so they render the same whether a pixel is
# wired GRB or RGB.
ALERT_COLORS = {
    "warning": (255, 255, 255),
    "caution": (255, 255, 0),
    "advisory": (0, 0, 255),
}

# Longest command line accepted; anything longer is discarded. Sized for
# `oled frame <base64>`: a 128x64 frame is 1024 bytes, 1368 in base64.
MAX_LINE = 2048

# Commands that draw on the framebuffer; refused while an alert owns the chain.
FRAME_COMMANDS = ("show", "blank", "clear", "off", "px", "bright", "cal")


def alert_level_factor(level, ms):
    """Brightness 0.0-1.0 of `level`'s pattern, `ms` after it took over."""
    if level == "warning":
        # 4 Hz strobe.
        return 1.0 if ms % 250 < 125 else 0.0
    if level == "caution":
        # Double blink every 1.5 s.
        p = ms % 1500
        return 1.0 if p < 120 or 240 <= p < 360 else 0.0
    # advisory: slow 4 s fade in and out, squared so it lingers near dark.
    f = 1.0 - abs((ms % 4000) / 2000.0 - 1.0)
    return f * f


def hex_to_rgb(s):
    """Parse 'ff8800' or '#ff8800' into an (r, g, b) tuple."""
    s = s.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError("color must be 6 hex digits, e.g. ff8800")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def build_label_index(elements):
    """Normalize the ELEMENTS map to {UPPER_LABEL: (idx, ...)}."""
    lut = {}
    for label, val in elements.items():
        idxs = (val,) if isinstance(val, int) else tuple(val)
        lut[str(label).upper()] = idxs
    return lut


# Status colors (kept dim; the onboard pixel is right next to your eyes).
ST_READY = (0, 40, 0)
ST_RX = (0, 0, 60)
ST_ERR = (60, 0, 0)


class Indicator:
    """Framebuffer + line-protocol controller."""

    def __init__(self):
        self.power = self._init_power()
        self.strip = neopixel.NeoPixel(
            config.DATA_PIN,
            config.NUM_PIXELS,
            brightness=config.DEFAULT_BRIGHTNESS,
            auto_write=False,
            pixel_order=config.PIXEL_ORDER,
        )
        self.color = tuple(config.DEFAULT_COLOR)
        self.labels = build_label_index(config.ELEMENTS)
        self.serial = usb_cdc.data
        self.status = self._init_status()
        self.oled = None
        self.oled_error = None
        if getattr(config, "OLED", False):
            try:
                import oled  # pylint: disable=import-outside-toplevel

                self.oled = oled.Oled(config)
            except Exception as e:  # noqa: BLE001 - keep the pixels working
                self.oled_error = str(e)

        # Calibration state.
        self.mode = "normal"
        self.cal_index = 0
        self.cal_map = {}

        # Alert state.
        self.alerts = set()
        self.alert_top = None
        self.alert_t0 = 0
        self.alert_shown = None
        self.saved_frame = None

        self.blank()
        self.set_status(ST_READY)

    # --- hardware helpers ---------------------------------------------------

    def _init_power(self):
        pin = getattr(config, "POWER_PIN", None)
        if pin is None:
            return None
        power = digitalio.DigitalInOut(pin)
        power.switch_to_output(value=True)
        return power

    def _init_status(self):
        if getattr(config, "STATUS_PIN", None) is None:
            return None
        try:
            return neopixel.NeoPixel(
                config.STATUS_PIN, 1, brightness=0.3, auto_write=True
            )
        except Exception:  # noqa: BLE001 - status LED is best-effort
            return None

    def set_status(self, rgb):
        if self.status is not None:
            self.status[0] = rgb

    def blank(self):
        self.strip.fill((0, 0, 0))
        self.strip.show()

    def emit(self, msg):
        """Send a reply to the host data port and echo to the REPL console."""
        if self.serial is not None:
            try:
                self.serial.write((msg + "\n").encode("utf-8"))
            except Exception:  # noqa: BLE001 - host may not be listening
                pass
        print(msg)

    # --- normal-mode commands ----------------------------------------------

    def cmd_show(self, arg):
        tokens = [t.strip().upper() for t in arg.split("+") if t.strip()]
        if not tokens:
            raise ValueError("show needs an expression, e.g. show A+B")
        indices = []
        unknown = []
        for t in tokens:
            if t in self.labels:
                indices.extend(self.labels[t])
            else:
                unknown.append(t)
        if unknown:
            raise ValueError("unknown element(s): " + ", ".join(unknown))
        self.strip.fill((0, 0, 0))
        for i in indices:
            self._check_index(i)
            self.strip[i] = self.color
        self.strip.show()
        return "ok show " + "+".join(tokens)

    def cmd_px(self, arg):
        parts = arg.split()
        if not parts:
            raise ValueError("px needs indices, e.g. px 0,2,5 ff0000")
        color = hex_to_rgb(parts[1]) if len(parts) > 1 else self.color
        idxs = [int(x) for x in parts[0].split(",") if x != ""]
        if not idxs:
            raise ValueError("px needs indices, e.g. px 0,2,5 ff0000")
        for i in idxs:
            self._check_index(i)
            self.strip[i] = color
        self.strip.show()
        return "ok px " + parts[0]

    def cmd_color(self, arg):
        self.color = hex_to_rgb(arg)
        return "ok color %02x%02x%02x" % self.color

    def cmd_bright(self, arg):
        v = int(arg)
        if not 0 <= v <= 100:
            raise ValueError("brightness must be 0..100")
        self.strip.brightness = v / 100.0
        self.strip.show()
        return "ok bright %d" % v

    def _check_index(self, i):
        if not 0 <= i < config.NUM_PIXELS:
            raise ValueError(
                "pixel %d out of range 0..%d" % (i, config.NUM_PIXELS - 1)
            )

    # --- alerts -------------------------------------------------------------

    def alerts_reply(self):
        active = [lvl for lvl in ALERT_LEVELS if lvl in self.alerts]
        return "ok alerts " + (",".join(active) if active else "none")

    def cmd_alert(self, arg):
        level = arg.strip().lower()
        if level not in ALERT_LEVELS:
            raise ValueError("alert level must be one of: " + ", ".join(ALERT_LEVELS))
        if not self.alerts:
            self.saved_frame = [tuple(self.strip[i]) for i in range(config.NUM_PIXELS)]
        self.alerts.add(level)
        return self.alerts_reply()

    def cmd_ack(self, arg):
        level = arg.strip().lower()
        if level in ("", "all"):
            self.alerts.clear()
        elif level in ALERT_LEVELS:
            self.alerts.discard(level)
        else:
            raise ValueError("ack takes a level or nothing: " + ", ".join(ALERT_LEVELS))
        return self.alerts_reply()

    def tick(self):
        """Advance the alert animation; restore the frame after the last ack."""
        top = None
        for lvl in ALERT_LEVELS:
            if lvl in self.alerts:
                top = lvl
                break
        now = time.monotonic_ns() // 1000000
        if top != self.alert_top:
            self.alert_top = top
            self.alert_t0 = now
            self.alert_shown = None
            if top is None and self.saved_frame is not None:
                for i, rgb in enumerate(self.saved_frame):
                    self.strip[i] = rgb
                self.strip.show()
                self.saved_frame = None
        if top is None:
            return
        f = alert_level_factor(top, now - self.alert_t0)
        r, g, b = ALERT_COLORS[top]
        rgb = (int(r * f), int(g * f), int(b * f))
        if rgb != self.alert_shown:
            self.strip.fill(rgb)
            self.strip.show()
            self.alert_shown = rgb

    # --- calibration --------------------------------------------------------

    def cmd_cal(self, _arg):
        self.mode = "cal"
        self.cal_index = 0
        self.cal_map = {}
        self._cal_light()
        return (
            "cal: pixel 0 lit. Type the label that projects (e.g. 5), or: "
            "skip / back / done / abort"
        )

    def _cal_light(self):
        self.strip.fill((0, 0, 0))
        if 0 <= self.cal_index < config.NUM_PIXELS:
            self.strip[self.cal_index] = self.color
        self.strip.show()

    def cal_input(self, line):
        s = line.strip()
        low = s.lower()
        if low == "abort":
            self.mode = "normal"
            self.blank()
            return "cal: aborted"
        if low == "done":
            return self._cal_finish()
        if low == "back":
            self.cal_index = max(0, self.cal_index - 1)
            self._cal_light()
            return "cal: pixel %d lit" % self.cal_index

        label = None if (low == "skip" or s == "") else s
        if label is not None:
            self.cal_map[label] = self.cal_index
        prev = self.cal_index
        self.cal_index += 1
        if self.cal_index >= config.NUM_PIXELS:
            return self._cal_finish()
        self._cal_light()
        note = ("recorded %s->%d" % (label, prev)) if label else "skipped"
        return "cal: %s, pixel %d lit" % (note, self.cal_index)

    def _cal_finish(self):
        self.mode = "normal"
        self.blank()
        self.labels = build_label_index(self.cal_map)  # apply live for testing
        items = ", ".join('"%s": %d' % (k, v) for k, v in self.cal_map.items())
        return (
            "cal: done (applied live). Paste into config.py:\n"
            "ELEMENTS = {" + items + "}"
        )

    # --- dispatch -----------------------------------------------------------

    def handle(self, line):
        if self.mode == "cal":
            return self.cal_input(line)
        s = line.strip()
        if not s:
            return None
        parts = s.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        try:
            if cmd == "alert":
                return self.cmd_alert(arg)
            if cmd == "ack":
                return self.cmd_ack(arg)
            if cmd == "alerts":
                return self.alerts_reply()
            if self.alerts and cmd in FRAME_COMMANDS:
                return "err alert latched; ack it before " + cmd
            if cmd == "show":
                return self.cmd_show(arg)
            if cmd in ("blank", "clear", "off"):
                self.blank()
                return "ok blank"
            if cmd == "px":
                return self.cmd_px(arg)
            if cmd == "color":
                return self.cmd_color(arg)
            if cmd in ("bright", "brightness"):
                return self.cmd_bright(arg)
            if cmd == "cal":
                return self.cmd_cal(arg)
            if cmd == "oled":
                if self.oled is None:
                    return "err no oled: " + (self.oled_error or "config.OLED not set")
                return self.oled.handle(arg)
            if cmd == "ping":
                return "ok pong"
            if cmd == "help":
                return HELP
            return "err unknown command: " + cmd
        except Exception as e:  # noqa: BLE001 - report to host, keep running
            return "err " + str(e)


def main():
    ind = Indicator()
    if ind.serial is None:
        print(
            "USB data serial is not enabled. Confirm boot.py contains "
            "usb_cdc.enable(console=True, data=True) and POWER-CYCLE the board "
            "(soft reset is not enough)."
        )
    ind.emit("indicator ready. type 'help'.")
    if ind.oled_error:
        ind.emit("err oled: " + ind.oled_error)

    buf = b""
    serial = ind.serial
    while True:
        if serial is not None and serial.in_waiting:
            buf += serial.read(serial.in_waiting)
            if b"\n" not in buf and len(buf) > MAX_LINE:
                # A line that never ends would eventually exhaust RAM and
                # crash code.py, leaving an alert light silently dark.
                buf = b""
                ind.emit("err line too long")
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("utf-8", "replace").rstrip("\r")
                ind.set_status(ST_RX)
                resp = ind.handle(line)
                if resp is not None:
                    ind.emit(resp)
                ind.set_status(ST_ERR if (resp or "").startswith("err") else ST_READY)
        if ind.oled is not None and (serial is None or not serial.in_waiting):
            # Refresh only once the burst of commands is drained.
            ind.oled.refresh()
        ind.tick()
        time.sleep(0.005)


main()
