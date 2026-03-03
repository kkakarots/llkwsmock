import argparse
import logging
import time
from typing import Optional

import foxglove
import mcap.reader
import mcap.records
from foxglove import Channel, Schema
from foxglove.websocket import WebSocketServer

channels: dict[str, Channel] = {}
scene_cache: dict[str, tuple[Channel, bytes]] = {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--rate", type=float, default=1.0)  # 播放倍率
    args = parser.parse_args()

    file_name = args.file

    server = foxglove.start_server(
        name=file_name,
        port=args.port,
        host=args.host,
    )

    print(f"Foxglove WebSocket running at ws://{args.host}:{args.port}")

    try:
        while True:
            stream_once(file_name, server, args.rate)
            logging.info("Looping playback...")
            server.clear_session()

    except KeyboardInterrupt:
        server.stop()


def stream_once(file_name: str, server: WebSocketServer, rate: float):
    global scene_cache
    scene_cache.clear()

    with open(file_name, "rb") as f:
        reader = mcap.reader.make_reader(f)

        for mcap_schema, mcap_chan, mcap_msg in reader.iter_messages():

            channel = get_channel(mcap_schema, mcap_chan)

            # 如果是 SceneUpdate，缓存但不立刻发送
            if mcap_schema and mcap_schema.name == "foxglove.SceneUpdate":
                scene_cache[mcap_chan.topic] = (channel, mcap_msg.data)
                continue

            channel.log(
                mcap_msg.data,
                log_time=time.time_ns(),
            )

            # 控制发送速率（避免瞬间打满）
            time.sleep(0.001 / rate)

    # 文件播放完后，发送静态 SceneUpdate
    for topic, (channel, data) in scene_cache.items():
        print(f"Re-sending static SceneUpdate: {topic}")
        channel.log(
            data,
            log_time=time.time_ns(),
        )


def get_channel(
    mcap_schema: Optional[mcap.records.Schema],
    mcap_channel: mcap.records.Channel,
) -> Channel:
    """
    根据 MCAP 中的信息创建或获取 Channel
    """
    if mcap_channel.topic in channels:
        return channels[mcap_channel.topic]

    channels[mcap_channel.topic] = Channel(
        topic=mcap_channel.topic,
        message_encoding=mcap_channel.message_encoding,
        schema=(
            None
            if mcap_schema is None
            else Schema(
                name=mcap_schema.name,
                encoding=mcap_schema.encoding,
                data=mcap_schema.data,
            )
        ),
    )

    print(
        f"Registered topic: {mcap_channel.topic} | "
        f"encoding={mcap_channel.message_encoding} | "
        f"schema={None if mcap_schema is None else mcap_schema.name}"
    )

    return channels[mcap_channel.topic]


if __name__ == "__main__":
    main()