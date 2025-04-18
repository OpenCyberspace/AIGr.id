#!/bin/bash

curl -X POST http://$SERVER_URL/api/createvDAG \
  -H "Content-Type: application/json" \
  -d @./vadg.json