#!/bin/bash


cd gst-build/
meson configure build/ -Dgst-plugins-bad:nvcodec=enabled;
ninja -C build/;
