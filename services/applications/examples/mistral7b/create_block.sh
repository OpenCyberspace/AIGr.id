#!/bin/bash


curl -X POST http://$SERVER_URL/api/createBlock \
  -H "Content-Type: application/json" \
  -d @./block.json
