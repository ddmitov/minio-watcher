#!/usr/bin/env python3.8

import asyncio
import json
import signal
import sys

import aioredis

tasks = None
redis = None


def shutdown_handler(signum, frame):
    global tasks

    redis.close()
    redis.wait_closed()

    for task in tasks:
        if not task.cancelled():
            task.cancel()

    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)


async def minio_watcher_stderr_reader(minio_watcher_stderr_stream):
    while True:
        minio_stderr_line = await minio_watcher_stderr_stream.readline()

        if minio_stderr_line:
            print(minio_stderr_line.decode('UTF-8'))
        else:
            break


async def minio_watcher_stdout_reader(minio_watcher_stdout_stream, redis):
    while True:
        minio_stdout_line = await minio_watcher_stdout_stream.readline()

        if minio_stdout_line:
            stdout_json = json.loads(minio_stdout_line.decode('UTF-8'))

            time = stdout_json['events']['time']
            path = stdout_json['events']['path']
            size = stdout_json['events']['size']

            print('|| ', time, ' || ', path, ' || ', size, ' ||')

            await redis.xadd(
                'test-stream',
                {
                    'time': time,
                    'path': path,
                    'size': size
                }
            )
        else:
            break


async def minio_watcher(event_loop, tasks):
    global redis

    minio_watcher_process = await asyncio.create_subprocess_exec(
        'mc',
        '--config-dir',
        '/mc/',
        'watch',
        '--events',
        'put',
        '--recursive',
        '--json',
        'minio-server/testing-bucket/',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    minio_watcher_stdout_task = event_loop.create_task(
        minio_watcher_stdout_reader(minio_watcher_process.stdout, redis)
    )

    tasks.append(minio_watcher_stdout_task)

    minio_watcher_stderr_task = event_loop.create_task(
        minio_watcher_stderr_reader(minio_watcher_process.stderr)
    )

    tasks.append(minio_watcher_stderr_task)


def main():
    global tasks
    global redis

    event_loop = asyncio.new_event_loop()
    tasks = []

    redis = aioredis.from_url('redis://redis:6380')

    minio_runner_task = event_loop.create_task(
        minio_watcher(event_loop, tasks)
    )

    tasks.append(minio_runner_task)

    event_loop.run_forever()


if __name__ == '__main__':
    asyncio.run(main())
