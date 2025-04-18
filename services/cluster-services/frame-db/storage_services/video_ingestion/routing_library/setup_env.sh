#!/bin/bash


pushd /gst-build/routing_client

    #install plugins
    pushd gst_plugin
        ./install.sh
    popd

    #run the app
    python3 

popd