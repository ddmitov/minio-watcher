FROM minio/mc:latest

RUN microdnf update --nodocs
RUN microdnf install python38 python38-pip

RUN pip3 install --no-cache \
    aioredis \
    asyncio

CMD ["python"]
