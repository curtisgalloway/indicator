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

"""Runs once at boot, before code.py.

Enables a SECOND USB serial (CDC) channel so the host can send commands on a
data port while the REPL/console stays free for debugging. code.py talks to
``usb_cdc.data``; you keep the REPL on ``usb_cdc.console``.

NOTE: changes here only take effect after a full power-cycle or hard reset
(the auto-reload soft reset does NOT re-run boot.py). If `usb_cdc.data` is
None at runtime, you have not power-cycled since copying this file.
"""

import usb_cdc

usb_cdc.enable(console=True, data=True)
