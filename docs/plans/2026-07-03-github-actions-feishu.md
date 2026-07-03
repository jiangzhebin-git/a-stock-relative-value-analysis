# GitHub Actions Feishu Notification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在无需本地电脑开机的情况下，每日运行四股分析并通过飞书发送新信号或失败通知。

**Architecture:** GitHub Actions 负责调度与运行，Python 通知脚本负责格式化和发送；分析结果与去重状态提交回私有仓库。Webhook 使用 GitHub Secret 注入。

**Tech Stack:** GitHub Actions, Python, requests, Feishu custom bot webhook

---

### Task 1: 创建飞书通知客户端

读取 `new_alerts.csv`，生成简洁中文通知；支持失败消息、空信号静默和 dry-run。

### Task 2: 创建自动化工作流

配置交易日北京时间15:35运行、手动触发、依赖缓存、测试、分析、通知、产物上传及结果回写。

### Task 3: 加固仓库与密钥说明

忽略虚拟环境和临时文件，提供 Secret 配置说明，确保Webhook不入库。

### Task 4: 测试

测试消息格式化、空事件和失败消息，运行完整测试套件并验证工作流YAML结构。

### Task 5: GitHub发布

初始化Git仓库；若GitHub CLI已登录则创建私有仓库、配置Secret并推送，否则等待用户完成GitHub授权和提供飞书Webhook。
