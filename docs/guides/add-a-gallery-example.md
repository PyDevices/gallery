# Add a gallery example

An example you drop into `lib/examples/` shows up in the gallery, in the
install manifests and on the site once you regenerate. This page covers what
to put in the file, what the generator does with it, and how to see it run in a
browser before you open a pull request.

Write the file itself in the house example style, summed up at the end of
[AGENTS.md](../../AGENTS.md): the three SPDX licence lines, then a docstring
with `Needs:`, `Run it:` and `Tested on:`. This page covers only what the
gallery adds on top.

## Where the file goes

The generator picks up every entry point under `lib/examples/`:

| Layout | Entry point |
|---|---|
| `examples/<name>.py` | a single file |
| `examples/<name>/<name>.py` | a package; this one is preferred |
| `examples/<name>/__init__.py` | a package with no `<name>.py` |

A package gets its own mip manifest, `packages/<name>.json`, so a board can
install the app and everything it needs with one `mip.install` call.

## Headers

Put these comments in the first 10 lines of the entry point, above or around
the licence lines. The generator ignores a header on line 11 or later.

| Header | What it says |
|---|---|
| `# deps: palettes, lvgl` | The packages the example imports. The browser page installs them. |
| `# utils: console, tft_config` | Helper modules from `lib/utils/` the example uses. They show as badges on the card. |
| `# modules: calc_engine` | Other example files, by name without `.py`, the page must load beside this one. |
| `# manifests: alien` | Packages from `packages/` the page installs. |
| `# gallery: featured` | How the example is listed. Values combine with commas. |

The values for `# gallery:` are:

- `featured` puts the card first.
- `skip` keeps the example out of the web gallery. Use it for a support file or
  an example that needs hardware a browser doesn't have.
- `binaries` also keeps it out of the web gallery, exactly like `skip`. Use it
  for an example that ships files mip can't carry (see below); the name tells
  the next reader why it's out.
- `newwindow` opens the demo in its own tab, for one too big to read beside the
  cards.
- `nochrome` opens it in its own tab on a bare page with none of the site's
  header and footer.

An unknown value stops the generator with an error, so a typo shows up at once.

## Declare what you import

If the example imports `palettes`, `pygraphics`, `pdwidgets`,
`audioinstruments`, `audioeffects` or `controlkit`, list it in `# deps:`. The
generator fails when one of those six is imported and not declared, and prints
a warning when you declare a package the example never imports. `audiodsp`
counts as imported when the example imports one of its modules, such as
`synthio` or `audiopump`. No other name
is checked, so a dependency outside those six is on you to get right: run the
example in a browser, as below, and see whether it loads.

## What mip installs

A mip package carries `.py`, `.mpy`, `.json` and `.html` files and nothing else.
The `.html` is there because some apps serve their own page from the board.
Images, `.bmp` files, sound files and shell scripts stay out of the manifest:
they're too big for most boards, and no board app serves them.

An example that needs one of those files either builds it in code or uses
`# gallery: binaries` and tells the reader where to get the file in its
docstring.

## Regenerate

From the repository root, with the [PyDevices](https://github.com/PyDevices/pydevices)
repository cloned beside it:

```bash
./scripts/install_refresh_manifests.sh
python scripts/gallery_generator.py
```

The first command rewrites `packages/` and `gallery.toml` from what is in
`lib/`. The second updates the gallery cards in `.site/gallery/index.html` and
the file list the site stages, and captures a thumbnail for any example that
has none. Commit what both produce.

To see what would change before you apply it, run
`./scripts/install_refresh_manifests.sh --audit`. It regenerates, prints the
differences and puts your files back, but it rewrites the tree for a moment, so
don't run it in a checkout someone else is using.

## Check it

```bash
python scripts/gallery_generator.py --check
```

This writes nothing. It fails when a generated file is stale, when a header is
wrong or when a dependency is missing, which is the same check CI runs. The
generator looks for the PyDevices checkout in the folder beside this one and in
every folder above it, so it also works from a git worktree you create under
`.worktrees/`.

## Thumbnails

The generator captures a missing thumbnail by running the example on the
desktop for two seconds at 240x320 and saving
`.site/pyscript/thumbnails/<name>.png`. If that capture is wrong, because the
first frame is blank or the app needs a moment longer, capture your own and
replace the file:

```bash
python tools/screenshot.py lib/examples/alien.py 4 --resolution 240x320 --scale 0.5 -o .site/pyscript/thumbnails/alien.png
```

The number after the file is how many seconds to wait before the shot.

## Try it in a browser

The gallery page loads the MicroPython runtime from the site's `/vendor/`
folder, so serving `.site/gallery/` alone fails with a failed import. Serve a
folder that has both:

```bash
mkdir /tmp/gallery-site
ln -s /path/to/PyDevices.github.io/vendor /tmp/gallery-site/vendor
ln -s "$PWD/.site/gallery" /tmp/gallery-site/gallery
python -m http.server 8000 --directory /tmp/gallery-site
```

Open `http://localhost:8000/gallery/micropython.html?modules=piano`, with your
own example's name in place of `piano`. A package example takes
`?manifests=<name>` instead. Both parameters take a comma-separated list, and
the first name is the one that runs.

The page tells scripts how it's doing in `globalThis.__pydevicesHost`.
`phase` goes from `"loading"` to `"ready"` or `"failed"`, and `errors` lists
what the program raised after it was ready. In the browser console:

```js
__pydevicesHost.phase   // "ready"
__pydevicesHost.errors  // []
```

A page waits for a click or key press before it turns the sound on, because
browsers require one. If your example plays audio, click the canvas first.

## Before you open the pull request

- `python scripts/gallery_generator.py --check` passes.
- You opened the example in a browser and it reached `"ready"` with no errors.
- The new `packages/`, `gallery.toml`, `.site/gallery/index.html` and thumbnail
  files are in the commit along with the example.
