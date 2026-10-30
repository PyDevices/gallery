# Roadmap

Planned work for the gallery. Bugs, and things you need that don't work yet,
go to [issues](https://github.com/PyDevices/gallery/issues).

## Apps

- google_photos: playlists. Keep several saved picks (Wedding, Christmas,
  Grandkids) and choose which one the frame shows.
- A live-audio example built on one object that owns the codec, the audio
  graph and the pump behind a safe surface: the way to build a live instrument.
- An MJPEG video player that plays a file from SD through `jpegio` onto any
  display, with its frame rate measured on an S3 with an SPI panel and on the
  P4's hardware decoder, and the ffmpeg line that makes the file.
- car_cluster: redraw the ring gauges and the hood with real radial gradients
  and vector art once the LVGL bindings support them. Waits on vector graphics
  in the build ([omnipython-lvgl's roadmap](https://github.com/PyDevices/omnipython-lvgl/blob/main/ROADMAP.md)).

## Site

- The gallery moves to its own address on the PyDevices domain, beside the
  site, the docs, the package index and workbench.
