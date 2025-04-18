#!/bin/bash

BUCKET_NAME=$1

AWS_HOST=$(kubectl -n default get cm $BUCKET_NAME -o yaml | grep BUCKET_HOST | awk '{print $2}')
AWS_ACCESS_KEY_ID=$(kubectl -n default get secret $BUCKET_NAME -o yaml | grep AWS_ACCESS_KEY_ID | awk '{print $2}' | base64 --decode)
AWS_SECRET_ACCESS_KEY=$(kubectl -n default get secret $BUCKET_NAME -o yaml | grep AWS_SECRET_ACCESS_KEY | awk '{print $2}' | base64 --decode)

echo "Ceph-AWS host-name: $AWS_HOST"
echo "Ceph-AWS access key id: $AWS_ACCESS_KEY_ID"
echo "Ceph-AWS Access key: $AWS_SECRET_ACCESS_KEY"
