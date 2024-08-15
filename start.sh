#!/bin/sh

mkdir -p ./minio-server
mkdir -p ./minio-client

DOCKER_USER=$(id -u):$(id -g) docker-compose up
