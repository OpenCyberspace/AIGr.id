#!/bin/bash


docker build . -t registry.ai-platform.com/models/mistral7b-vllm-external:2.0.0

docker push registry.ai-platform.com/models/mistral7b-vllm-external:2.0.0