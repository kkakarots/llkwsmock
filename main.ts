import { McapIndexedReader } from "@foxglove/mcap";
import { FoxgloveServer } from "@foxglove/ws-protocol";
import { fs } from "fs/promises";

async function runMockServer() {
  // 1. 初始化服务器
  const server = new FoxgloveServer({ name: "mcap-mock-server" });
  server.listen(8765);
  console.log("Mock Server 运行在 ws://localhost:8765");

  // 2. 读取 MCAP 文件
  const fileHandle = await fs.open("./example.mcap");
  const reader = await McapIndexedReader.Initialize(fileHandle);

  // 3. 将 MCAP 中的 Channels 映射到 WebSocket 广播
  const channelMap = new Map();
  for (const [id, channel] of reader.channels) {
    // 将 MCAP 的频道信息通告给前端
    const serverChanId = server.addChannel({
      topic: channel.topic,
      schemaName: channel.schemaName,
      schema: channel.schema,
      encoding: channel.messageEncoding, // 这里的 encoding 通常是 'ros1msg' 或 'cdr' (ros2)
      metadata: channel.metadata,
    });
    channelMap.set(id, serverChanId);
  }

  // 4. 处理前端订阅
  server.on("subscribe", (chanId) => {
    console.log(`前端订阅了话题 ID: ${chanId}`);
    
    // 5. 模拟回放：遍历所有消息并推送
    // 注意：实际应用中这里应该根据消息时间戳进行延时，模拟“实时”
    (async () => {
      for await (const message of reader.readMessages()) {
        const serverChanId = channelMap.get(message.channelId);
        if (serverChanId === chanId) {
          // 发送二进制原始数据
          server.sendMessage(
            serverChanId, 
            message.logTime, // 使用录制时的时间戳
            message.data     // 直接发送二进制 Buffer
          );
          // 稍微停顿一下，防止瞬间发完（模拟回放速度）
          await new Promise(r => setTimeout(r, 10)); 
        }
      }
    })();
  });
}

runMockServer().catch(console.error);