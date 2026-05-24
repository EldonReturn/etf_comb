## Why

当前系统只支持预定义的时间周期（1m、3m、6m、1y、2y、3y、5y），用户无法选择自定义的起始时间点。这限制了用户在特定历史时间段进行回测分析的能力，例如分析2020年疫情期间或2008年金融危机期间ETF的表现。添加自定义起始日期功能可以让用户进行更精确的历史绩效分析。

## What Changes

- **前端**：在 OptimizerPanel 组件中添加日期选择器，允许用户选择自定义起始日期替代预定义周期
- **后端**：扩展 `period` 参数支持 ISO 8601 格式日期字符串（如 `2020-01-01`）
- **API**：修改 `/portfolio/optimize`、`/portfolio/evaluate`、`/portfolio/compare` 端点支持自定义日期范围
- **UI优化**：当用户选择自定义日期时，隐藏或禁用预定义周期选择器

### Out of Scope (Non-Goals)

- 不支持自定义结束日期（固定为当前日期）
- 不支持选择特定日期区间的精确开始/结束日期选择器
- 不修改数据库 schema

## Capabilities

### New Capabilities

- `custom-date-range`: 自定义分析日期范围 — 允许用户指定分析起始日期，系统自动计算到当前的日期范围
- `api-start-date`: API 接受 start_date 参数 — 后端 API 端点接受可选的 ISO 8601 格式 `start_date` 参数替代 `period`
- `backward-compatibility`: 向后兼容现有 period 参数 — 当 `start_date` 未提供时，系统行为与原有预定义周期完全一致

## Risks & Mitigations

| 风险 | 缓解措施 |
|------|----------|
| 起始日期早于 ETF 上市日期 | 后端使用 ETF 实际最早 NAV 日期作为起点，返回警告 |
| 用户选择未来日期 | 前端 date picker `max` 属性限制为当前日期 |
| 时间段过短（< 30 天）无统计意义 | 后端/前端设置最小 30 天阈值，显示警告提示 |

## Impact

- **前端**：`frontend/src/components/OptimizerPanel.tsx` — 添加日期输入控件
- **后端**：`backend/services/optimizer_service.py`、`backend/services/portfolio_service.py` — 扩展 `period_to_days()` 和 `get_etf_nav_series()` 函数支持日期解析
- **API**：`/portfolio/optimize`、`/portfolio/evaluate`、`/portfolio/compare` 端点 — 修改请求体支持 `start_date` 参数
- **数据库**：无需更改 schema，现有的 NAV 数据已包含历史记录

### 行为影响

- **用户**：OptimizerPanel 新增"自定义起始日期"模式切换，原有预定义周期选择行为完全保留
- **API 消费者**：现有的只有 `period` 的请求行为不变，可选新增 `start_date` 字段

## Acceptance Criteria (Definition of Done)

- [ ] 用户可通过 OptimizerPanel 选择自定义起始日期并执行优化
- [ ] 选择早于 ETF 上市日的日期时，系统使用实际最早数据并显示警告
- [ ] 选择未来日期时，前端阻止提交并显示验证错误
- [ ] 选择不足 30 天的范围时，显示数据不足警告
- [ ] 不使用自定义日期时，所有预定义周期（1m/3m/6m/1y/2y/3y/5y）行为不变
- [ ] 三个 API 端点（optimize/evaluate/compare）均支持 `start_date` 参数
- [ ] 现有测试全部通过，新增边界条件测试覆盖

## Open Questions

这些问题的决策不影响当前最小可行版本（MVP），可在后续迭代中处理：

1. 是否需要支持自定义"结束日期"？（当前仅支持起始日期）
2. 自定义日期范围是否需要保存在用户偏好设置中？
3. 是否需要提供"最近 N 个交易日"而非日历日的选项？
