#!/usr/bin/env python3
"""量一下你的歌曲相对作者参考轨偏了多少毫秒。

片子的每一个镜头、每一句词的起音，都是对着作者那份 320 kbps MP3 定死的。
你自己的拷贝（不同平台、不同压缩、片头静音长短不同）常常整体早/晚几十毫秒，
在 24 fps 下 42 ms 就是一帧——对齐与否肉眼看得出来。

本仓库自带作者的 1 ms 响度包络：film/pv_dsh_frontend_20260927/wave_rms_1ms.npy。
这里解出你的 input/song.mp3 的同一包络，取 12 个强瞬态点做互配，给出中位偏移。

    python macos/check_song_alignment.py                     # 检查 input/song.mp3
    python macos/check_song_alignment.py path/to/other.mp3   # 检查别的文件

输出 `median delta: +127 ms` 表示你的音频整体晚 127 ms，可用：

    ffmpeg -i input/song.flac -af "atrim=start=0.127,asetpts=PTS-STARTPTS,apad=whole_dur=211.913" \\
           -c:a libmp3lame -b:a 320k -ar 44100 -ac 2 input/song.mp3

把它拉回来（|delta| < 10 ms 就不必动）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

def find_ref() -> Path | None:
    """参考包络：命令行 --ref 优先，否则在当前目录往下找 wave_rms_1ms.npy。"""
    if "--ref" in sys.argv:
        return Path(sys.argv[sys.argv.index("--ref") + 1])
    hits = sorted(Path.cwd().rglob("wave_rms_1ms.npy"))
    return hits[0] if hits else None


def envelope(path: Path, sr: int = 48000) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    hop = sr // 1000
    n = len(x) // hop
    return np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--") and not a.endswith(".npy")]
    song = Path(args[0]) if args else Path("input/song.mp3")
    if not song.exists():
        print(f"找不到 {song}（用法：check_song_alignment.py <歌曲> [--ref <包络.npy>]）")
        return 1
    ref_path = find_ref()
    if ref_path is None or not ref_path.exists():
        print("找不到参考包络 wave_rms_1ms.npy（用 --ref 指定）")
        return 1
    print(f"参考包络: {ref_path}")
    ref = np.load(ref_path).astype(np.float64)
    env = envelope(song)
    print(f"song : {song}")
    print(f"len  : {len(env) / 1000:.3f} s   (参考 {len(ref) / 1000:.3f} s)")

    # 12 个强瞬态点（响度上升最陡的位置），在 ±400 ms 内找本地峰值
    d = np.diff(ref[: min(len(ref), 200000) - 1])
    idx = sorted(np.argsort(d)[-40:])
    picks: list[int] = []
    for i in idx:
        if picks and i - picks[-1] < 2000:
            continue
        picks.append(int(i))
    picks = picks[:12]

    offs = []
    for p in picks:
        a, b = max(0, p - 50), min(len(env), p + 400)
        if b <= a:
            continue
        pk = a + int(np.argmax(env[a:b]))
        offs.append(pk - p)
        print(f"  ref {p:7d} ms -> song {pk:7d} ms  delta {pk - p:+4d} ms")

    arr = np.array(offs)
    med = int(np.median(arr))
    print(f"\nmedian delta: {med:+d} ms   (|delta| < 10 ms 视为已对齐；42 ms = 1 帧)")
    if abs(med) >= 10:
        print(f"建议裁/补 {abs(med) / 1000:.3f} s，见本文件顶部注释里的 ffmpeg 命令。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
