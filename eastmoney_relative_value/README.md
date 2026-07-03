# 资本市场活跃度敏感股票相对价值分析工具

独立分析东方财富、同花顺、指南针和财富趋势，用大盘指数、证券板块、
两市成交活跃度及个股量能解释合理日收益率。项目只提供量化辅助分析，不自动交易。

## 快速开始

```powershell
cd eastmoney_relative_value
python -m pip install -r requirements.txt
python main.py --start 2016-01-01 --end 2026-07-03 --force
```

首次运行通过 AkShare 获取数据并写入 `data/`；后续默认使用缓存，传入 `--force` 可更新。若网络更新失败但已有缓存，程序自动回退到缓存。

## 输出

- `data/<股票代码>/raw_stock_*.csv`：上市以来或近十年原始日线
- `data/<股票代码>/raw_intraday_*_5m.csv`：接口实际可得的5分钟线
- `output/<股票代码>/`：每只股票独立模型、回测、图表和报告
- `output/multi_stock_summary.csv`：四股横向结果
- `output/multi_stock_summary_report.md`：横向报告
- `output/alerts.csv`、`alerts.json`：通知系统可消费的信号事件
- `output/new_alerts.csv`：去重后的本次新增事件

只分析部分股票：

```powershell
python main.py --symbols 300033 300803 688318
```

## 方法口径

- 个股采用前复权日线；证券板块用 399975 代理。东方财富行情主接口断连时，
  自动降级到 AkShare 新浪行情；该接口没有指数成交额，届时用指数收盘×成交量代理
  市场活跃度变化率，并在运行日志中标记。
- 四组 Ridge 模型使用扩展窗口样本外预测，以减少共线性与过拟合。
- 理论价格为前收盘乘以预测收益；信号当日收盘后产生，回测在下一交易日开盘执行。
- 挂单带宽综合 ATR 与 20 日收益波动率。
- 回测暂未计手续费、滑点和涨跌停无法成交，应将结果视为研究基线。
- 指南针2019年上市、财富趋势2020年上市，不存在完整十年交易数据；程序保留其
  上市以来全部可得日线。免费分钟接口覆盖有限，报告会明确实际起止时间。
- `daily_start/daily_rows` 表示保留的完整日线，`analysis_start/analysis_rows`
  表示扣除初始训练窗口后真正参与样本外评估的数据。

## 测试

```powershell
pytest -q
```

## GitHub Actions 与飞书通知

仓库工作流位于 `.github/workflows/daily-analysis.yml`，每个交易日北京时间
15:35 自动执行，也可在 GitHub Actions 页面手动运行。

部署要求：

1. 使用私有 GitHub 仓库保存项目、历史CSV和告警状态。
2. 在飞书群创建自定义机器人并复制Webhook。
3. 在 GitHub 仓库 `Settings → Secrets and variables → Actions` 中创建
   `FEISHU_WEBHOOK_URL`，值为完整Webhook地址。
4. 在仓库 `Settings → Actions → General` 中将 Workflow permissions 设为
   `Read and write permissions`，供任务回写缓存和报告。

运行逻辑：

- 分析成功且出现新信号：发送飞书通知。
- 分析成功但没有新信号：保持安静。
- 分析失败：发送任务失败通知。
- 每次结果作为30天Artifact保留，并将数据、报告和去重状态提交回私有仓库。

真实Webhook不得写入 `.env.example`、代码或提交记录。

## 四股动态偏离网页

网页位于 `web/`，只展示东方财富、同花顺、指南针和财富趋势。页面不要求输入
价格；GitHub Actions在A股交易时段约每10分钟生成一次实时快照，页面的“刷新数据”
按钮会绕过浏览器缓存读取最新结果。

日终分析发布唯一的 `output/model_registry.json`。飞书、日报和网页使用同一组正式
模型及每只股票自己的系数；盘中任务只替换实时市场输入，不重新训练参数。

需要在GitHub Actions Secrets中增加：

- `WEB_ACCESS_PIN`：4位或6位数字。它会在部署时转换为SHA-256摘要。

该PIN是轻量访问阻挡，不是强认证。网页不应存储持仓、资金、Webhook或其他敏感数据。

## 风险提示

本模型仅基于历史数据和统计关系，用于辅助分析，不构成投资建议。市场可能受到政策、财报、流动性、突发事件、监管变化、公司基本面变化等影响，模型存在失效风险。任何买入、卖出或挂单操作都需要人工确认。
