#!/bin/bash

./run_block.sh blk-ksshxpiy 17000 17001
./run_block.sh blk-bfl3gbd5 17010 17011
./run_block.sh blk-tsonq3qr 17020 17021

docker run -d --rm --net=host --name=executor-blk-ksshxpiy \
    --env="BLOCK_ID=blk-ksshxpiy"  \
    --env="MODE=test" \
    executor:v1

docker run -d --rm --net=host --name=executor-blk-ksshxpiy-proxy \
    executor_proxy:v1