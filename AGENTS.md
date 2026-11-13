# AGENTS.md

- Adding an example: [docs/guides/add-a-gallery-example.md](docs/guides/add-a-gallery-example.md) has the headers, the dependency rule and the regenerate and check steps.
- `packages/`, `gallery.toml`, `.site/gallery/index.html` and `.site/pyscript/thumbnails/` are generated. Edit the example, run `./scripts/install_refresh_manifests.sh` and `python scripts/gallery_generator.py`, and commit the output.
- `./scripts/install_refresh_manifests.sh --audit` rewrites the tree for a moment before it restores it. Run it in a git worktree nobody else is using.
- `gallery_generator.py` needs a PyDevices/pydevices checkout beside this repository or above it. A worktree under `.worktrees/` finds it; one outside the tree doesn't.
- `# gallery:` and `# deps:` headers count only in the first 10 lines. An unknown `# gallery:` value stops the generator.
- Only `.py`, `.mpy`, `.json` and `.html` files go into a mip manifest. Images and other binaries are left out.
- The generator enforces `# deps:` only for palettes, pygraphics, pdwidgets, audioinstruments, audioeffects and controlkit. Declare any other import yourself and try the page in a browser.
- CI's style check tests four things: the SPDX lines on `.py` files, no Sphinx roles in docstrings, no links from the README or docs to the `.github` repository, and no README badge row. It doesn't look at docstring order or annotations.
