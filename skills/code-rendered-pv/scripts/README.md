# 脚本说明

三个脚本只依赖 `numpy` + `Pillow` + `ffmpeg`，可直接在任意工程里跑。

| 脚本 | 用法 | 关键参数 |
|---|---|---|
| `check_av_sync.py` | `python check_av_sync.py <成片> <歌曲> <提示音wav>` | `--dur 211.9`（目标时长）、`--chime-ms 207873`（提示音延后毫秒） |
| `check_song_alignment.py` | `python check_song_alignment.py <歌曲> [--ref <包络.npy>]` | 不传 `--ref` 时在当前目录往下找 `wave_rms_1ms.npy` |
| `prepare_character.py` | `python prepare_character.py <插画> <输出目录>` | 画布尺寸与阈值是**工程相关**常量，换工程要改文件头部的 `SPRITE_CANVAS` / `DANCER_CANVAS` / `BG_TOL` |

## 什么时候用哪个

- **开工前**：`check_song_alignment.py`（你的歌和参考轨差几毫秒？差 >10 ms 就该裁/补）
- **换素材后**：`prepare_character.py`（一张插画 → 抠图 / 立绘 / 舞者三套画布）
- **交付前**：`check_av_sync.py`（封装偏移、事件帧落点、漂移）

## 判读基线（一次真实交付的实测）

| 项 | 健康值 |
|---|---|
| 成片音轨 vs 应有混音 | lag 0 样本，相关 > 0.999 |
| 歌曲 vs 参考包络 | \|median delta\| < 10 ms |
| 事件帧落点 | 设计时刻 ± 0 帧 |
| 分窗漂移 | 中位 0 帧（24 fps 下即 < 41.7 ms） |
