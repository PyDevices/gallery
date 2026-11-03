#!/usr/bin/env python3
"""Assemble Synth Station's page: its Python as one bundle, beside a runtime of its own.

    python scripts/build_synthstation.py _site/synthstation

An installed copy has to keep working when the rest of the site moves on, so
the page pins what it runs in ``synthstation.lock``: a commit of the apps repo,
of pydevices (for midiports) and of the site (for the WebAssembly runtime).
``--apps``, ``--pydevices`` and ``--site`` take checkouts instead, to try a
change before it's pinned.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ORG = "https://github.com/PyDevices/"
SITE_REPO = "PyDevices.github.io"
#: What the app imports from the apps repo.
APP_PATHS = (
    "lib/appkit", "lib/controlkit", "lib/touchkit", "lib/spectrum", "lib/soundmodule", "lib/songmodel",
    "apps/__init__.py", "apps/synthstation/*.py", "apps/synthstation/app.json",
)
#: Only the pieces of midiports a browser reads.
MIDIPORTS = "packages/midiports/midiports/"
MIDIPORTS_FILES = ("__init__.py", "webmidi.py")
RUNTIME = ("micropython.mjs", "micropython.wasm")
SKIPPED_FOLDERS = ("/tests/", "/examples/", "/docs/")


def checkout(repo, commit, into):
    """A shallow copy of one commit."""
    into.mkdir(parents=True)
    for args in (("init", "-q"), ("fetch", "-q", "--depth", "1", ORG + repo, commit), ("checkout", "-q", "FETCH_HEAD")):
        subprocess.run(["git", "-C", str(into), *args], check=True)
    return into


def app_files(apps):
    """Paths in the apps repo, relative, that the page carries."""
    listed = subprocess.run(["git", "-C", str(apps), "ls-files", *APP_PATHS],
                            check=True, capture_output=True, text=True).stdout.split("\n")
    return [path for path in listed if path and not any(skip in "/" + path for skip in SKIPPED_FOLDERS)]


def bundle(apps, pydevices):
    """The bundle's bytes: a length, a JSON list of [path, offset, size], then the files."""
    sources = [(path, apps / path) for path in app_files(apps)]
    sources += [("lib/midiports/" + name, pydevices / MIDIPORTS / name) for name in MIDIPORTS_FILES]
    listing, blob = [], bytearray()
    for path, source in sorted(sources):
        data = source.read_bytes()
        listing.append([path, len(blob), len(data)])
        blob += data
    head = json.dumps(listing).encode()
    return struct.pack("<I", len(head)) + head + bytes(blob)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path, help="the page's folder in the assembled site")
    ap.add_argument("--apps", type=Path)
    ap.add_argument("--pydevices", type=Path)
    ap.add_argument("--site", type=Path)
    args = ap.parse_args()

    lock = json.loads((ROOT / "synthstation.lock").read_text())
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        apps = args.apps or checkout("apps", lock["apps"], work / "apps")
        pydevices = args.pydevices or checkout("pydevices", lock["pydevices"], work / "pydevices")
        site = args.site or checkout(SITE_REPO, lock["site"], work / "site")

        out = args.out
        if out.resolve() != (ROOT / ".site" / "synthstation").resolve():
            shutil.copytree(ROOT / ".site" / "synthstation", out, dirs_exist_ok=True)
        (out / "synthstation.bundle").write_bytes(bundle(apps, pydevices))
        for name in RUNTIME:
            shutil.copyfile(site / "vendor" / "micropython" / name, out / name)

    # The version covers everything the service worker caches.
    digest = hashlib.sha256()
    for path in sorted(p for p in out.iterdir() if p.is_file() and p.name != "sw.js"):
        digest.update(path.read_bytes())
    worker = out / "sw.js"
    worker.write_text(worker.read_text().replace("__VERSION__", digest.hexdigest()[:16]))
    print("built", out, digest.hexdigest()[:16])


if __name__ == "__main__":
    main()
