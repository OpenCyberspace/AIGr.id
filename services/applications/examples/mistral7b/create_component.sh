#!/bin/bash


curl -X POST http://$SERVER_URL/api/addComponent \
  -H "Content-Type: application/json" \
  -d @./component.json