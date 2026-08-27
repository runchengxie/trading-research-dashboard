# Maintenance hardening plan

## Goal

收尾当前项目的代码质量事项，补齐可重复运行的类型检查、覆盖率门槛和 Redis 集成验证，同时完成历史脚本与大文件的调用方审计。

## Scope

1. 修复 Dashboard 动态配置和可选 `backtrader` 的类型边界，并把 `ty` 纳入 CI。
2. 为 R-Breaker 的纯逻辑和运行时边界补测试，建立可逐步提高的 Dashboard coverage 门槛。
3. 增加使用真实 Redis 服务的集成测试，覆盖状态写入、心跳、Pub/Sub 和连接失败。
4. 审计大文件、wrapper、一次性脚本及兄弟仓库调用方。暂不删除无法证明无调用方的历史入口。
5. 记录仍需真实环境验证的 provider、Redis 和 WebSocket 重连场景，并完成全套本地验证。
