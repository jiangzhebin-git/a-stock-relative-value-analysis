from pathlib import Path

from src.live_snapshot import update_snapshot


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    snapshot = update_snapshot(
        root / "output" / "model_registry.json",
        root / "web" / "live_snapshot.json",
    )
    print(f"已更新 {len(snapshot['stocks'])} 只股票，时间 {snapshot['generated_at']}")

