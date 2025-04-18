#!/bin/bash

helm repo add datawire https://www.getambassador.io

kubectl create namespace ambassador
helm install ambassador --namespace ambassador --values=values/values.yaml datawire/ambassador