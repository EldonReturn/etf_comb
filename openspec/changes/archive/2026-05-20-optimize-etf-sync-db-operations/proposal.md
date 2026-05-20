## Why

全量ETF同步（sync_all_etf_data）在处理约800只ETF时存在严重的数据库性能问题。当前实现逐ETF提交写入，每个ETF约500条历史净值记录，导致大量的小事务提交（600+次commit），同步时间过长（超过20分钟），数据库写入成为瓶颈。

## What Changes

- 批量写入优化：将逐ETF的insert改为批量合并写入，大幅减少事务提交次数
- 减少数据库会话切换：在批量获取数据后统一写入，避免频繁的session创建和销毁
- 添加写入缓冲：累积一定数量记录后再写入，减少I/O次数
- 优化ETF数据清理策略：按批次而非全量清理，减少锁竞争

## Capabilities

### Modified Capabilities
- `etf-sync`: ETF数据同步流程的性能优化，核心改动在数据写入层

## Impact

- `backend/services/etf_data_service.py`: sync_all_etf_data函数重构
- `backend/db/database.py`: 数据库会话管理可能需要调整
- 同步耗时预计从20分钟降至3分钟以内