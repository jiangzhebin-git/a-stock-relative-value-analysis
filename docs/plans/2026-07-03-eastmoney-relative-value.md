# Eastmoney Relative Value Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建可重复运行的东方财富相对市场活跃度分析、模型比较、回测、可视化和报告工具。

**Architecture:** 采用模块化 Python 流水线：获取与缓存原始数据，构建无未来函数特征，以滚动时间序列样本外预测比较四组 Ridge 模型，再生成偏离信号、次日执行回测、图表和 Markdown 报告。网络失败时复用缓存，关键数据缺失时输出可操作错误。

**Tech Stack:** Python, pandas, numpy, akshare, scikit-learn, statsmodels, matplotlib, seaborn, scipy, pytest

---

### Task 1: 建立项目骨架和配置

创建 `eastmoney_relative_value/src`、数据输出目录、依赖文件、README、公共常量和日志配置。

### Task 2: 实现数据获取与预处理

实现 AkShare 多候选接口、CSV 缓存、中文字段标准化、指数与成交额对齐，并保存清洗数据。

### Task 3: 实现特征、相关性和滞后分析

计算收益率、量价变化、ATR、波动率、趋势过滤条件，以及同日和 1/2/3/5/10 日相关性。

### Task 4: 实现四模型样本外比较

用扩展窗口 TimeSeriesSplit 和 Ridge 生成样本外理论收益率，计算 R²、MAE、RMSE、方向准确率并保存系数。

### Task 5: 实现偏离信号与回测

生成理论价格、偏离等级、波动率自适应挂单区间、风险等级；以次日开盘价执行单仓位策略并输出完整绩效。

### Task 6: 实现图表、报告和入口

生成要求的八类 PNG、Markdown 报告、每日摘要和命令行入口。

### Task 7: 测试与端到端验证

用合成市场数据执行单元与集成测试，运行 `pytest -q`，再执行离线演示流水线确认所有交付物可生成。
