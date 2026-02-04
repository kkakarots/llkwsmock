import foxglove
import time

from foxglove.schemas import Log, LogLevel, Timestamp

server = foxglove.start_server(host="127.0.0.1", port=8765)

print("Foxglove server started")
while True:
    foxglove.log(
        "/hello",
        Log(
            timestamp=Timestamp.now(),
            level=LogLevel.Info,
            message="Hello, Foxglove!",
        )
    )

    time.sleep(0.033)
