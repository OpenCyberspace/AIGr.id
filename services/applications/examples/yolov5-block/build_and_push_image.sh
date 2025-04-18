#!/bin/bash


docker build . -t registry.ai-platform.com/models/object-detector:2.0.0

docker push registry.ai-platform.com/models/object-detector:2.0.0