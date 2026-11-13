#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial", "pillow"]
# ///
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

"""Host-side CLI to drive the NeoPixel readout module over USB serial.

This file is a self-contained uv script: the header above lists its
dependencies, so it runs directly (`./host/indicator.py ...`) or through a
symlink on PATH, with uv fetching pyserial and Pillow into a cached
environment on first use:
    ln -s /path/to/indicator/host/indicator.py ~/.local/bin/indicator
    indicator --list
    indicator --auto show 5
    indicator --port /dev/tty.usbmodem1234 show A+B
    indicator --port /dev/tty.usbmodem1234   # interactive

OLED boards (boards/kb2040_oled.py) also take two commands that are
handled on this side before anything is sent:
    write <line> [<line> ...]   clear the screen and show up to 8 text lines;
                                `write -` reads the lines from stdin
    image <file> [--threshold N] [--invert]
                                scale a picture to fit, convert it to black
                                and white (dithered unless --threshold), and
                                send it as one frame
Everything else, such as `oled text 0 16 2 Hi`, goes to the board as typed.

The board exposes TWO serial ports (console + data). Commands must go to the
DATA port. --auto probes candidates with `ping` and picks the one that answers
`ok pong`.

Exit status for a one-shot command: 0 ok; 1 the board answered
`ok alerts none` (nothing latched; use `|| true` under `set -e`); 2 the board
replied `err` or the arguments were bad; 3 no board found; 22 no reply, so
whether the command took effect is unknown -- check with `alerts`.
"""

import argparse
import base64
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("pyserial required: run the file directly so uv installs it",
          file=sys.stderr)
    sys.exit(3)

EXIT_OK = 0
EXIT_EMPTY = 1
EXIT_USAGE = 2
EXIT_PRECONDITION = 3
EXIT_RETRY_UNKNOWN = 22


def candidates():
    # USB devices first: probing a Bluetooth serial port can stall, and the
    # board is always a USB device.
    ports = sorted(list_ports.comports(), key=lambda p: (p.vid is None, p.device))
    return [p.device for p in ports]


def probe(dev, baud):
    """Return True if `dev` is the indicator's data port (answers ping)."""
    try:
        with serial.Serial(dev, baud, timeout=0.4) as s:
            time.sleep(0.2)
            s.reset_input_buffer()
            s.write(b"ping\n")
            time.sleep(0.2)
            reply = s.read(s.in_waiting or 1).decode("utf-8", "replace")
            return "pong" in reply
    except (OSError, serial.SerialException):
        return False


def autodetect(baud):
    for dev in candidates():
        if probe(dev, baud):
            return dev
    return None


def send(dev, baud, line):
    """Send one command, print the reply, and return an exit status for it."""
    with serial.Serial(dev, baud, timeout=0.5) as s:
        time.sleep(0.2)
        s.write((line + "\n").encode("utf-8"))
        time.sleep(0.15)
        reply = s.read(s.in_waiting or 1).decode("utf-8", "replace")
    sys.stdout.write(reply)
    if not reply.strip():
        print("error: no reply from %s; the command may or may not have taken "
              "effect" % dev, file=sys.stderr)
        return EXIT_RETRY_UNKNOWN
    if reply.startswith("err"):
        return EXIT_USAGE
    if reply.strip() == "ok alerts none":
        return EXIT_EMPTY
    return EXIT_OK


def send_many(dev, lines):
    """Send several commands on one connection; return an exit status.

    Waits for each reply before the next command, so a long frame line is
    never interleaved with the next command.
    """
    for line in lines:
        if "\n" in line or "\r" in line:
            raise ValueError("command contains a line break: %r" % line[:40])
    status = EXIT_OK
    with serial.Serial(dev, timeout=2) as s:
        time.sleep(0.2)
        s.reset_input_buffer()
        for line in lines:
            s.write((line + "\n").encode("utf-8"))
            reply = s.readline().decode("utf-8", "replace")
            if not reply:
                print("error: no reply to %r from %s" % (line[:40], dev),
                      file=sys.stderr)
                return EXIT_RETRY_UNKNOWN
            if reply.startswith("err"):
                sys.stderr.write(reply)
                status = EXIT_USAGE
    return status


# Text geometry of the firmware's 5x8 font on a 128x64 panel.
OLED_COLS = 21
OLED_ROWS = 8
OLED_W = 128
OLED_H = 64


def write_lines(dev, texts):
    """Clear the OLED and show `texts`, one per row, cut to fit."""
    if texts == ["-"]:
        texts = sys.stdin.read().splitlines()
    if len(texts) > OLED_ROWS:
        print("warning: only the first %d lines fit" % OLED_ROWS, file=sys.stderr)
    cmds = ["oled clear"]
    for row, text in enumerate(texts[:OLED_ROWS]):
        # A line break inside an argument would end this command early and
        # send the rest to the board as a command of its own.
        text = "".join(c if c.isprintable() else " " for c in text)
        cmds.append("oled line %d %s" % (row, text[:OLED_COLS]))
    return send_many(dev, cmds)


def image_frame(path, threshold=None, invert=False):
    """Return a 128x64 picture as 1024 bytes in the SSD1306 page layout."""
    try:
        from PIL import Image, ImageOps  # pylint: disable=import-outside-toplevel
    except ImportError:
        print("Pillow required: run the file directly so uv installs it",
              file=sys.stderr)
        sys.exit(EXIT_PRECONDITION)
    img = ImageOps.exif_transpose(Image.open(path)).convert("L")
    img = ImageOps.pad(img, (OLED_W, OLED_H), color=0)
    if invert:
        img = ImageOps.invert(img)
    if threshold is None:
        img = img.convert("1")  # Floyd-Steinberg dithering
    else:
        img = img.point(lambda v: 255 if v >= threshold else 0).convert("1")
    px = img.load()
    out = bytearray(OLED_W * OLED_H // 8)
    for page in range(OLED_H // 8):
        for x in range(OLED_W):
            byte = 0
            for bit in range(8):
                if px[x, page * 8 + bit]:
                    byte |= 1 << bit
            out[page * OLED_W + x] = byte
    return bytes(out)


def send_image(dev, words):
    ap = argparse.ArgumentParser(prog="image")
    ap.add_argument("file")
    ap.add_argument("--threshold", type=int, help="0-255 cutoff instead of dithering")
    ap.add_argument("--invert", action="store_true")
    a = ap.parse_args(words)
    frame = image_frame(a.file, a.threshold, a.invert)
    return send_many(dev, ["oled frame " + base64.b64encode(frame).decode("ascii")])


def interactive(dev, baud):
    print("connected to %s -- type commands, Ctrl-D to quit" % dev)
    with serial.Serial(dev, baud, timeout=0.5) as s:
        time.sleep(0.2)
        try:
            while True:
                line = input("> ")
                s.write((line + "\n").encode("utf-8"))
                time.sleep(0.15)
                sys.stdout.write(s.read(s.in_waiting or 1).decode("utf-8", "replace"))
        except EOFError:
            print()


def main():
    ap = argparse.ArgumentParser(description="Drive the NeoPixel readout module.")
    ap.add_argument("--port", help="serial device of the CircuitPython DATA port")
    ap.add_argument("--auto", action="store_true", help="auto-detect the data port")
    ap.add_argument("--baud", type=int, default=115200, help="ignored by USB CDC")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("words", nargs=argparse.REMAINDER,
                    help="command to send, e.g. show A+B, or write/image")
    args = ap.parse_args()

    if args.list:
        for dev in candidates():
            print(dev)
        return EXIT_OK

    dev = args.port
    if args.auto or not dev:
        found = autodetect(args.baud)
        if not found:
            print("error: could not auto-detect the data port; use --list then "
                  "--port", file=sys.stderr)
            return EXIT_PRECONDITION
        dev = found

    if args.words and args.words[0] == "write":
        return write_lines(dev, args.words[1:])
    if args.words and args.words[0] == "image":
        return send_image(dev, args.words[1:])
    if args.words:
        return send(dev, args.baud, " ".join(args.words))
    interactive(dev, args.baud)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
