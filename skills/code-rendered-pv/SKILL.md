---
name: code-rendered-pv
description: 用代码逐帧渲染一支 PV / 视频（每一帧是歌曲时间 t 的纯函数），包括把任意插画、歌曲、文案、配色接进现成工程，以及逐帧画面验收和 A/V 同步校验。Use when the user wants a code-rendered music video / PV, wants to swap assets into an existing per-frame pipeline, wants to re-skin or re-text a rendered film, or wants frame-by-frame or A/V verification of a finished video.
---

# 代码渲染的 PV：制作、改造与逐帧验收

这类片子没有剪辑软件，没有手工关键帧：**每一帧是 `t` 的纯函数**，由 Python 画出来，或由 Playwright 把 HTML 截成图，最后 ffmpeg 合成。本技能给的是这套东西的工作流、提示词模板，以及真踩过的坑。

先读 `references/workflow.md`（七步流程与闸门）；要下指令给子代理时用 `references/prompt-templates.md`；动手改素材/配色前**必读** `references/pitfalls.md`；交付前按 `references/verification.md` 验收。

## 三条铁律

1. **先冒烟，再评估。** 用替代品（静音假歌、临时字体、替身素材）把最小闭环跑通，再上真素材。纸面评估必漏：格式假设、编码器参数、硬编码路径、裁剪框，全靠真跑才暴露。
2. **每个偏差都要记账并复验。** 「发现偏了 127 ms」不算修好；量出 127 → 修 → 复量得 +4 ms 才算。没复验的修复等于没修。
3. **验收必须可量化。** 帧数、时长、音量 dB、对齐毫秒、蓝/粉色像素占比、切点邻域帧差——不是「看着还行」。

## 七步

| # | 步骤 | 闸门 |
|---|---|---|
| 0 | **定性**：这是什么、交付物是什么形态、边界（可否发布/商用/改名） | 交付物与验收口径说得出来 |
| 1 | **盘点**：工具链、素材、权限、磁盘、时间，逐项实查 | 缺口 ≤3 且都有替代 |
| 2 | **冒烟**：替代品跑通最小闭环 | 端到端能出东西，哪怕 4 秒 |
| 3 | **补缺**：换真素材，换不了的记账 | 每处替换有文档、可回滚 |
| 4 | **全量**：正式构建 | 退出码 0 + 产物齐全 |
| 5 | **验收**：量化自检 | 全部达标或偏差已量化 |
| 6 | **固化**：setup / run / check 三件套 | 换台机器照文档能从零复现 |

## 实测标定（M4 Pro，1280×720 / 24 fps / 212 s / 5086 帧）

| 环节 | 耗时 | 备注 |
|---|---|---|
| 网页截图 4968 张（Playwright） | ≈400 s | 最大头；约 80 ms/帧 |
| 逐帧渲染 5086 帧（12 进程 PIL） | 60–250 s | 取决于段落的特效密度 |
| 交付编码（x264 CRF16 720p） | ≈15 s | |
| 4K（x265 3840×2160，从无损母版升） | 224 s | 母版 ×3 最近邻，不插值 |
| **换素材整版重出** | ≈8 min | 截图 + 渲染 |

## 改造现成工程时的五类坑（详见 pitfalls.md）

一套「同一概念、多处常量」是这类工程最典型的坑：**换素材往往只对上了一部分**。

1. **坐标系常量**：立绘裁剪框、虹膜坐标、身体比例，各自写死在 CSS / PIL / 缓存三套坐标里。换素材必须逐套核对。
2. **渲染期替换**：`sprite_src` 在渲染期可能被别的模块顶替（读缓存帧而非立绘文件），你改的文件根本没被加载。
3. **烤进截图的文字**：左窗（HTML 截图）里的文案改了必须重跑截图；右窗（PIL）改完只需重渲。
4. **配色**：十六进制、RGB 元组、通道斜坡（`int(10+70*v)` 这种）三种写法并存；改完用像素统计验证，别信肉眼。
5. **辉光/后期**：小面积高饱和元素会被 bloom 提亮，设计值 ≠ 成片值——取色要比目标再压一档。

## 命令速查（macOS）

```bash
# 环境
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python pillow numpy
npm install && npx playwright install chromium   # 约 557 MB 缓存
export PV_F_MONO=... PV_F_MONO_B=... PV_F_CJK=... PV_F_SYM=...   # Windows 字体必须换

# 出片
.venv/bin/python build.py check
.venv/bin/python build.py all            # 或 pages / render 分开跑
.venv/bin/python build.py render --4k

# 只看几帧（快）
cd film/pv_dsh_frontend_*/ && ../../.venv/bin/python dsh_her.py stills 8.5 30 110 165 209.5
```

## 自带脚本

| 脚本 | 用途 |
|---|---|
| `scripts/check_av_sync.py` | A/V 校验：封装偏移、事件帧落点、分窗漂移 |
| `scripts/check_song_alignment.py` | 量你的歌曲相对参考轨的毫秒偏移（用作者的 1 ms 响度包络） |
| `scripts/prepare_character.py` | 任意插画 → 抠图 / 立绘 / 舞者三套画布 |

用法与判读基线见 `scripts/README.md`；三个脚本只依赖 numpy + Pillow + ffmpeg。

## 自带模板

| 文件 | 用途 |
|---|---|
| `templates/setup-macos.sh` | 幂等装配：Python 3.12 venv / Playwright / 字体 → 生成 `pv-env.sh` |
| `templates/run.sh` | 一键出片，自动带字体环境变量 |

把两个文件放到工程根目录即可用。

## 一条提醒

这类工程的**画面即代码**，所以「改字」等于改源码。改之前先用 `references/pitfalls.md` 里的 grep 清单把常量位置全找出来，否则会像本技能的由来一样：以为改完了，其实还有三套坐标没对。
