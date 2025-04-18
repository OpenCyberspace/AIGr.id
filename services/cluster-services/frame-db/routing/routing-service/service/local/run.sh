#!/bin/bash

set -a 
source .env 
set +a

cd ..
uvicorn main:app
