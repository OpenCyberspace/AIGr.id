#!/bin/bash


#run this file to start the docker

#NOTE : These parameters can affcet the resource utilization

ROUTING_URI="http://localhost:8000"
ROUTING_API="/routing/getMapping"

ROUTING_PUBSUB_HOST="localhost"
ROUTING_PUBSUB_PORT="6379"
ROUTING_PUBSUB_PASSWORD="Friends123#"

CAMERA_ID="test-local-3"

docker run --gpus "device=0" -e NVIDIA_DRIVER_CAPABILITIES=all \
--network=host \
--rm -ti \
-e ROUTING_URI=${ROUTING_URI} \
-e ROUTING_API=${ROUTING_API} \
-e ROUTING_PUBSUB_HOST=${ROUTING_PUBSUB_HOST} \
-e ROUTING_PUBSUB_PORT=${ROUTING_PUBSUB_PORT} \
-e ROUTING_PUBSUB_PASSWORD=${ROUTING_PUBSUB_PASSWORD} \
-v ${PWD}:/framedb-ingestion \
-v ${PWD}/gst-python-build.1.19.0.1.build:/gst-build/gst-python/meson.build \
 streamer:latest

#ngcognitiai/gstremer:2080Ti_cuda10.1
# streamer
# gstdoc:latest

#ngcognitiai/gstremer:2080Ti_cuda10.1
 

#