"""Print live dBFS levels from an RTSP stream so you can see what noises produce what levels.

Usage: python tests/log_audio.py [rtsp_url] [--csv levels.csv] [--min-db -60]
"""
import argparse
import csv
import sys
import threading
import time
from pathlib import Path

# Running `python tests/log_audio.py` only puts tests/ on sys.path, so add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.routes.audio import watch_loud_noise

BAR_WIDTH = 50


def bar(level_db: float, min_db: float) -> str:
    fraction = min(max((level_db - min_db) / (0 - min_db), 0.0), 1.0)
    filled = round(fraction * BAR_WIDTH)
    return "#" * filled + "-" * (BAR_WIDTH - filled)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rtsp_url", nargs="?", default="rtsp://localhost:8554/webcam")
    parser.add_argument("--csv", help="also append timestamp,dbfs rows to this file")
    parser.add_argument("--min-db", type=float, default=-60.0, help="left edge of the level bar")
    parser.add_argument("--window", type=float, default=0.5)
    parser.add_argument("--interval", type=float, default=0.25)
    args = parser.parse_args()

    csv_file = open(args.csv, "a", newline="") if args.csv else None
    writer = csv.writer(csv_file) if csv_file else None
    levels: list[float] = []
    start = time.time()

    def on_level(_name: str, level_db: float) -> None:
        levels.append(level_db)
        print(f"{time.time() - start:7.2f}s  {level_db:7.1f} dBFS  |{bar(level_db, args.min_db)}|", flush=True)
        if writer and csv_file:
            writer.writerow([f"{time.time():.3f}", f"{level_db:.2f}"])
            csv_file.flush()

    stop = threading.Event()
    print(f"Listening to {args.rtsp_url} (Ctrl+C to stop). Bar spans {args.min_db:.0f} to 0 dBFS.")
    try:
        # A threshold below the -200 dBFS silence floor makes every evaluation report.
        watch_loud_noise(
            "log", args.rtsp_url, on_level, stop,
            threshold_db=-1000.0, window=args.window, interval=args.interval,
        )
    except KeyboardInterrupt:
        stop.set()
    finally:
        if csv_file:
            csv_file.close()

    if levels:
        print(f"\n{len(levels)} readings: min {min(levels):.1f}, "
              f"avg {sum(levels) / len(levels):.1f}, max {max(levels):.1f} dBFS")


if __name__ == "__main__":
    main()
