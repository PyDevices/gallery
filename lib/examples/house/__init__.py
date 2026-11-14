# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

# gallery: skip
# The house appliance's modules import each other by name (house_panel), and
# the sensor hub as a package, so importing this package puts its own
# directory and its parent on the path. Casting needs the castdisplay package
# and the ESP32-P4 firmware with castif.
import sys

_wd = __file__.replace("\\", "/")
_wd = _wd.rsplit("/", 1)[0] if "/" in _wd else "."
_parent = _wd.rsplit("/", 1)[0] if "/" in _wd else ".."
for _p in (_wd, _parent):
    if _p not in sys.path:
        sys.path.append(_p)
