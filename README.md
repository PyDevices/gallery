# Gallery

The gallery is a set of showcase apps for the PyDevices stack: a piano, a
spectrum analyzer, games, dashboards, a TV remote, a photo viewer and more.
Each one draws with the same code on a MicroPython-compatible board, a
CircuitPython-compatible board, a desktop window, a browser tab and an Android
phone.

## Try one in your browser

Open [pydevices.github.io/gallery](https://pydevices.github.io/gallery/),
choose an app and press run. Nothing to install.

## Run one on your computer

The apps live in `lib/examples`. From `lib/`, with the PyDevices stack
installed for your interpreter:

```bash
cd lib
micropython examples/piano.py
```

Apps with their own folder have a README with options and screenshots, for
example [spectrum](lib/examples/spectrum/README.md).

## Install one on a board

Each app folder has a manifest in `packages/`. On a board with Wi-Fi:

```python
import mip

mip.install("github:PyDevices/gallery/packages/alien.json")
```

Swap `alien` for any other file name in [packages/](packages/). The `utils`
manifest installs the shared helpers the apps import.

[Roadmap](ROADMAP.md)

Made by [PyDevices](https://pydevices.com).
