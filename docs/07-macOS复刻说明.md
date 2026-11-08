# macOS 复刻说明（本机实测）

上游：<https://github.com/MisakaZentai/world-execute-me-dsh-pv>
这份说明只记录 **在 macOS / Apple Silicon 上把这支片子重新渲出来** 需要的东西和踩过的坑。上游的 `README.md`、`docs/` 仍然有效，先读那边。

本机实测环境：MacBook Pro · Apple M4 Pro（14 核）· 48 GB · macOS 27.3 · arm64。

---

## 一分钟上手

```bash
./setup-macos.sh                 # Python 3.12 venv + pillow/numpy + Playwright + 字体 → 生成 pv-env.sh
# 把歌曲放到 input/song.mp3（见下一节）
.venv/bin/python macos/check_song_alignment.py   # 可选：检查音频对齐
./run.sh                         # = python build.py all
./run.sh all --4k                # 另出 3840×2160
```

产物：

| 文件 | 规格 | 本机大小 |
|---|---|---|
| `out/film.mp4` | 1280×720 / 24 fps / H.264 + AAC，211.9 s | 82.4 MB |
| `out/film_master.mp4` | 无损 RGB（gbrp）母版 | 657 MB |
| `out/film_4k.mp4` | 3840×2160 / 24 fps / HEVC（`--4k`） | 见下方实测 |

**全流程实测 461 秒**（截图 ≈400 s、渲染 ≈50 s、编码 ≈10 s）；只重渲不动截图时 `./run.sh render` **66 秒**。

---

## 一、歌曲（必须自备）

片子的每个镜头和每个唱词起音都是对着作者那份 `320 kbps / 44.1 kHz / 211.913 s` 的 MP3 定死的，**时间零点 = 该文件解码后的第一个采样**。

### 从网易云 `.ncm` 转（本机做法）

```bash
brew install ncmdump
ncmdump "$HOME/Music/网易云音乐/Mili/world.execute (me) ; - Mili.ncm" -o input/
# 它会解出 input/world.execute (me) ; - Mili.flac（这台机器上是 FLAC，不是 MP3）
```

### 对齐（重要）

不同来源的拷贝常常整体早/晚几十毫秒——**42 ms 就是一帧**，歌词条和镜头会错开。仓库自带作者的 1 ms 响度包络 `film/pv_dsh_frontend_20260927/wave_rms_1ms.npy`，用它量：

```bash
.venv/bin/python macos/check_song_alignment.py
# median delta: +127 ms   ← 表示你的音频整体晚 127 ms
```

这台机器上网易云那份就晚了 **127 ms**，修正方式（裁头 + 补尾到原时长）：

```bash
ffmpeg -y -i input/world.execute\ \(me\)\ \;\ -\ Mili.flac \
  -af "atrim=start=0.127,asetpts=PTS-STARTPTS,apad=whole_dur=211.913" \
  -c:a libmp3lame -b:a 320k -ar 44100 -ac 2 -map_metadata 0 input/song.mp3
```

修完再量一次应是 `|delta| < 10 ms`（本机 +4 ms）。

> 为什么必须补尾：`build.py` 的交付编码带 `-shortest`，音轨比 211.9 s 短就会把片子结尾一起截掉（第一次构建就因此出了 211.78 s）。

---

## 二、字体（已自动处理，但要知道代价）

上游把四个字体硬编码成 Windows 路径（`C:/Windows/Fonts/*`），`build.py check` 会因此报缺字体。macOS 上用环境变量覆盖（`setup-macos.sh` 生成的 `pv-env.sh`）：

| 变量 | 上游默认 | 这台机器 | 代价 |
|---|---|---|---|
| `PV_F_MONO` | `consola.ttf`（Consolas） | JetBrains Mono Regular | **字宽 0.55 em → 0.6 em，宽约 9%** |
| `PV_F_MONO_B` | `consolab.ttf` | JetBrains Mono Bold | 同上 |
| `PV_F_CJK` | `msyh.ttc`（微软雅黑） | 系统 PingFang.ttc | 字形不同，字宽基本一致 |
| `PV_F_SYM` | `seguisym.ttf` | 系统 STIX Two Math | ∃ ⟨ ⟩ ⊢ ∀ 齐全 |

- 作者在 `docs/FONTS.md` 里已写明「换了字体，字宽不同，部分排版会轻微错位」——这不是本机跑坏了，是既知代价。
- 左边的 dsh 窗口由 Chromium 渲染，走的是**系统 UI 字体**（原片 Segoe UI + 微软雅黑 → 本机 SF Pro + PingFang），行高与换行会变。改动它需要改 `seg.html` / `dsh_components.css` 并重新截图；**本机没有做**，因为手上没有原片可对齐，改了只是换一种偏离。
- 别下载 Menlo 之外的「Consolas 复刻」：Consolas 本身不可再分发。

---

## 三、本机与原片的差异（照旧存在）

1. **舞者替身**：仓库不含原片的 MMD→H3 生成帧，`tools/placeholder_h3.py` 会用鲸鱼娘立绘生成「站着摇摆」的替身。所有点云 / 样本格 / 特征图 / 热图画面因此与原片不同。想换：把同格式帧放进 `film/mmd_motion_eval_20260927/pv_cache/` 与 `continuity_full_v2/cache/h3_full_v1/`（格式见该工具文档字符串）。
2. **字体**：见上。
3. 作者自述：12.5–29 s 的检查点编号、123.5 s 前后 3 帧的发送键颜色，成片与这版代码不一致。
4. 作者自述：114.75–114.83 s、159–161 s 有未验证的后期亮度差（CPU/GPU 实现不同）。

---

## 四、踩过的坑

| 现象 | 原因 / 处理 |
|---|---|
| `python3 -V` 是 3.9.9，脚本跑不动 | 系统自带 Python 太老。用 `uv venv --python 3.12` 或 brew 的 `python@3.12`；3.13 也能跑（`build.py` 会自动挂 `audioop` shim），但 3.12 最省事 |
| `build.py check` 报 4 个 missing font | 上游硬编码 Windows 路径，先 `source ./pv-env.sh` |
| 成片比 211.9 s 短零点几秒 | `-shortest` + 音轨偏短；按上面「对齐」一节把音轨补到 211.913 s |
| `chcp`/编码报错 | 不需要；`build.py` 自己设了 `PYTHONUTF8=1` |
| `--gpu` 直接崩 | `dsh_gpu.py` 写死 `torch.device("cuda")`。720p 下 CPU 已经很够（全片渲染 50 s），不建议折腾 MPS |
| ffmpeg 报 `Unrecognized option 'vsync'` | ffmpeg 9 已移除 `-vsync`，改用 `-fps_mode` |
| 磁盘吃紧 | 完整构建 ≈1.6 GB（母版 657 MB + 截图 213 MB + Chromium 557 MB）；`--4k` 再加约 0.6 GB |
| Playwright 截图和被截图页码对不上 | 1.49 起 headless 默认走 `chromium-headless-shell`，与本机 Chrome 的字体路径不同；逐帧截图必须固定用同一个浏览器 |

---

## 五、本机新增的文件（都在 `.gitignore` 之外，未提交上游）

| 路径 | 用途 |
|---|---|
| `setup-macos.sh` | 幂等装配环境，生成 `pv-env.sh` |
| `pv-env.sh` | 四个字体环境变量 |
| `run.sh` | 一键出片（`all` / `check` / `pages` / `render` / `--4k`） |
| `macos/check_song_alignment.py` | 量你的歌曲相对参考轨的毫秒偏移 |
| `input/song.flac`、`input/song.mp3`、`input/song-untrimmed.mp3` | 本机歌曲（**受版权保护，不要提交/分发**） |
