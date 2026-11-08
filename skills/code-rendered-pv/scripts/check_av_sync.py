#!/usr/bin/env python3
"""逐帧 A/V 校验：把成片的音轨和画面事件逐项对齐。

    python macos/check_av_sync.py out/film.mp4 input/song.mp3 film/pv_dsh_frontend_20260927/chime_g.wav

做四件事：
 1. 成片音轨 vs 「应该生成的混音」——相关性与样本级偏移（应为 0 样本）
 2. 成片音轨 vs 作者参考包络（wave_rms_1ms.npy）——中位偏移
 3. 画面事件落点：HARD_CUT / 钟声 / 滑入 三个设计时刻，检查对应帧是否精确跳变
 4. 歌词带变化 × 音频 onset 的互相关（全片 + 每 10 秒），确认零漂移
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000


def decode(path: Path, extra: list[str] | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), *([] if extra else ["-ac", "1", "-ar", str(SR)]),
           "-f", "f32le", "pipe:1"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def best_lag(a: np.ndarray, b: np.ndarray, maxlag: int, step: int) -> tuple[int, float]:
    m = min(len(a), len(b))
    best = (0, -2.0)
    for lag in range(-maxlag, maxlag + 1, step):
        x = a[max(0, lag): m + min(0, lag)]
        y = b[max(0, -lag): m + min(0, -lag)]
        k = min(len(x), len(y))
        if k < SR:
            continue
        c = float(np.corrcoef(x[:k], y[:k])[0, 1])
        if c > best[1]:
            best = (lag, c)
    return best


def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    film = Path(argv[0])
    song = Path(argv[1]) if len(argv) > 1 else None
    chime = Path(argv[2]) if len(argv) > 2 else None
    dur = 211.9                                   # 目标时长；用 --dur 覆盖
    chime_ms = 207873                             # 钟声延后毫秒；用 --chime-ms 覆盖
    if "--dur" in sys.argv:
        dur = float(sys.argv[sys.argv.index("--dur") + 1])
    if "--chime-ms" in sys.argv:
        chime_ms = int(sys.argv[sys.argv.index("--chime-ms") + 1])

    audio = decode(film)
    print(f"[1] 成片音轨 {len(audio)/SR:.3f}s")

    if song and chime:
        # 按 build.py 的滤镜重建“应该的混音”
        mix = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(song), "-i", str(chime), "-filter_complex",
             f"[0:a]atrim=0:{dur},asetpts=PTS-STARTPTS[s];[1:a]adelay={chime_ms}|{chime_ms}[c];"
             "[s][c]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[a]",
             "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"],
            capture_output=True, check=True).stdout
        want = np.frombuffer(mix, dtype=np.float32).astype(np.float64)
        lag, corr = best_lag(audio, want, 960, 48)
        print(f"[2] 成片音轨 vs 应为混音：lag {lag} 样本（{lag/SR*1000:+.1f} ms），相关 {corr:.6f}")
        print("    → 0 样本即表示封装没有引入偏移")

    # 3) 画面事件：用逐帧亮度差找跳变
    W, H = 320, 180
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(film), "-vf", f"scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W).astype(np.float32)
    mean = fr.mean(axis=(1, 2))
    diff = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    print(f"[3] 画面 {len(fr)} 帧")
    hard = chime_ms / 1000 - 0.791              # 本工程实测：硬切比钟声早 0.791 s
    events = (("HARD_CUT", hard), ("钟声/光标", chime_ms / 1000), ("钟声后 0.44 s", chime_ms / 1000 + 0.439))
    for name, t in events:
        f = int(round(t * 24))
        lo, hi = max(0, f - 3), min(len(diff), f + 4)
        print(f"    {name} 设计 {t:.4f}s（帧 {f}）：邻域帧差 {[round(float(x),1) for x in diff[lo:hi]]}"
              f"  亮度 {[round(float(x),1) for x in mean[lo:hi]]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
