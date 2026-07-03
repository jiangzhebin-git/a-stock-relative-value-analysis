from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import requests

RISK_LINE = "仅用于量化辅助分析，不构成投资建议；任何操作都需要人工确认。"


def format_alerts(alerts: pd.DataFrame) -> str:
    if alerts.empty:
        return ""
    sections = ["【资本市场相对价值提醒】"]
    for row in alerts.itertuples(index=False):
        sections.append(
            "\n".join([
                f"{row.name}（{row.symbol}）",
                f"信号：{row.title}",
                f"实际价格：{float(row.actual_price):.2f} 元",
                f"理论价格：{float(row.theoretical_price):.2f} 元",
                f"偏离：{float(row.deviation_pct):+.2%}",
                f"风险等级：{row.risk_level}",
                f"建议：{row.advice}",
            ])
        )
    sections.append(f"数据时间：{pd.Timestamp(alerts.iloc[0]['date']):%Y-%m-%d}")
    sections.append(RISK_LINE)
    return "\n\n".join(sections)


def format_failure(details: str) -> str:
    return "\n".join([
        "【股票分析任务运行失败】",
        "今日数据或模型未能正常完成，请勿将未收到买卖信号理解为没有机会。",
        f"错误摘要：{details[:800]}",
        "请查看 GitHub Actions 日志。",
    ])


def send_text(webhook_url: str, text: str, timeout: int = 15) -> None:
    if not webhook_url:
        raise RuntimeError("缺少 FEISHU_WEBHOOK_URL")
    response = requests.post(
        webhook_url,
        json={"msg_type": "text", "content": {"text": text}},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code", payload.get("StatusCode", 0)) != 0:
        raise RuntimeError(f"飞书返回失败: {json.dumps(payload, ensure_ascii=False)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="发送飞书股票分析通知")
    parser.add_argument("--alerts", default="output/new_alerts.csv")
    parser.add_argument("--failure", help="发送任务失败通知")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    text = ""
    if args.failure:
        text = format_failure(args.failure)
    else:
        path = Path(args.alerts)
        if path.exists() and path.stat().st_size:
            text = format_alerts(pd.read_csv(path))
    if not text:
        print("没有新增信号，本次不发送飞书通知")
        return 0
    if args.dry_run:
        print(text)
        return 0
    send_text(os.environ.get("FEISHU_WEBHOOK_URL", ""), text)
    print("飞书通知发送成功")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

