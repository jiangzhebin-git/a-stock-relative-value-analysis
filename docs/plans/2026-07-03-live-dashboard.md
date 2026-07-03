# Live Four-stock Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 用同一已发布模型快照驱动飞书通知、日报和带PIN的四股盘中动态偏离网页。

**Architecture:** 日终流水线发布模型注册表；盘中轻量任务加载注册表、获取实时报价并生成快照；静态网页读取快照并展示四股卡片。GitHub Actions负责盘中更新和Pages部署。

**Tech Stack:** Python, pandas, requests, vanilla HTML/CSS/JavaScript, GitHub Actions, GitHub Pages

---

### Task 1: 发布统一模型注册表

从每日最佳模型、有效系数和最新信号生成版本化JSON，供通知与网页共同读取。

### Task 2: 实现盘中特征和快照

获取实时行情、按交易进度校正累计量能、应用正式系数；失败时降级静态结果并标注置信度。

### Task 3: 实现网页

创建PIN遮罩、刷新按钮、四股结果卡、数据年龄、加载/失败/过期状态和移动端布局。

### Task 4: 自动更新和部署

增加盘中GitHub Actions工作流与Pages发布流程；PIN哈希从GitHub Secret注入。

### Task 5: 统一通知

飞书消息改为读取统一实时/日终快照，确保偏离率和网页一致。

### Task 6: 测试与发布

测试注册表、时间进度、降级、偏离分级和前端数据契约，运行官方actionlint和云端工作流。
