#!/bin/bash

#install plugins
pushd /gst-build/video_ingestion/plugins
    chmod 777 install.sh
    ./install.sh
popd

#run the app
pushd /gst-build/video_ingestion/service
    python3 main.py
popd
