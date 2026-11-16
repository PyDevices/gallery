# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

WOKWI = True
TARGET = "/tmp/lib"

if WOKWI:
    import wifi

    wifi.connect_from_secrets()
    TARGET = "lib"


import mip  # noqa: E402

OMNIPYTHON_LIB = "https://lib.omnipython.org"
OMNIPYTHON = "github:PyDevices/omnipython"
OMNIPYTHON_EXAMPLES = "github:PyDevices/gallery"

# index= is required so bare deps like "displaydev" resolve from lib.omnipython.org
# (not micropython.org). The application installs optional appdev explicitly
# when it needs the non-LVGL event traffic controller.
mip.install(
    OMNIPYTHON + "/board_configs/busdisplay/spi/wokwi_ili9341_ft6x36_esp32s3/",
    index=OMNIPYTHON_LIB,
    target=TARGET,
)
mip.install("pygraphics", index=OMNIPYTHON_LIB, target=TARGET)
mip.install(OMNIPYTHON_EXAMPLES + "/lib/examples/testris.py", target=TARGET)

# isort: off
if WOKWI:
    import testris
