# Multi-stock Intraday Relative Value Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将东方财富工具扩展为四只资本市场活跃度敏感股票的独立建模、盘中观察与通知事件系统。

**Architecture:** 共享市场数据，按股票代码独立获取、建模、回测和输出；日线模型负责相对价值，分钟线负责最新中枢内定位。通知层读取标准化最新信号并生成去重事件。

**Tech Stack:** Python, pandas, numpy, AkShare, scikit-learn, matplotlib, seaborn, pytest

---

### Task 1: 参数化股票池和数据获取

将固定300059的数据接口改为股票配置驱动，增加300033、300803、688318及分钟线缓存与降级。

### Task 2: 参数化单股流水线

将清洗、特征、模型、偏离、回测、图表和报告在每只股票自己的目录中运行。

### Task 3: 生成横向汇总

输出每只股票数据区间、最佳模型、参数、偏离、风险、回测指标与最新建议。

### Task 4: 盘中相对位置

用最近日线理论中枢和波动带计算每根分钟K线的盘中偏离、区域和事件，保存CSV。

### Task 5: 通知事件

生成可供飞书、邮件或定时任务消费的CSV/JSON事件，并按股票、交易日和信号去重。

### Task 6: 测试与真实数据验证

补充股票配置、分钟字段、四股独立参数和通知去重测试；运行完整测试与真实数据流水线。
