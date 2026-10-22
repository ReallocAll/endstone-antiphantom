# AntiPhantom v0.1.0

首个版本：每位玩家可设置幻翼生成偏好，按照同维度玩家位置与 `tick-distance` 的模拟候选区块范围判定。

- `/phantom off` 关闭偏好；`/phantom on` 开启偏好；`/phantom status` 或 `/phantom` 查询状态和原因。新玩家默认开启。
- 覆盖同一区块的玩家全部关闭时才取消幻翼生成事件；任意覆盖玩家开启，或没有覆盖玩家时，保留原版行为。
- 偏好按 UUID 持久化；玩家消息为中文，服务器日志和控制台消息为英文。

## 安装

下载 `endstone_antiphantom-0.1.0-py3-none-any.whl`，放入 Endstone 的 `plugins` 目录，然后重启服务器。`SHA256SUMS` 提供 wheel 和源码包校验值。

- Python 3.11–3.15，Endstone API 0.11；测试使用 Endstone 0.11.14。
- 发布流程构建同一个纯 Python wheel，并在 Python 3.11–3.15 上安装该文件、运行 107 项自动化测试及独立入口加载检查。
- 区块几何依据用户提供的 Linux x86-64 BDS 1.26.52.3 IDA 分析。其他版本或平台需重新核验。

## 已知边界

- 尚未完成真实 BDS 服务器集成验证；自动化测试使用真实 Endstone SDK 和模拟宿主/玩家。
- `ActorSpawnEvent` 在实体加入世界后触发；取消事件会移除该实体，不是底层生成前拦截。事件没有生成原因，刷怪蛋和命令生成若经过同一事件，也可能受影响。
- 不清理已有幻翼，不阻止幻翼飞入，也不提供攻击保护。
- 自然生成仍要求全局 `doinsomnia` 开启并满足原版条件。插件不修改它，也无法通过当前公开 API 读取其运行时值。
- 范围表示模拟候选区块，不保证区块已经就绪或实体实际参与 tick。修改 `tick-distance` 后需重启服务器。

详细配置、持久化故障处理及[手动服务器验证清单](https://github.com/ReallocAll/endstone-antiphantom/blob/v0.1.0/docs/server-validation.md)见仓库文档。
