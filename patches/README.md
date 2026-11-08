# 源码改动补丁

`2026-11-08-达妮娅改造.patch` 是对上游工程的**全部源码改动**（40 个文件，2219 行），
基线是上游 master（commit `a598092`）。

包含：

| 类别 | 文件 |
|---|---|
| macOS 复刻支持 | `README-MACOS.md`、`run.sh`、`setup-macos.sh`、`macos/*.py` |
| 角色素材取景 | `tuikit.py`、`h3_full.py`、`f2_closeup.py`、`seg_page.py`、`batch_*.py` |
| 人格与文案 | `batch_a1~g.py`、`seg_page.py`、`seg.html`、`build_frame.py` |
| 品牌清除 / 鸣潮化 | `facts.py`、`scenes_*.py`、`kit.py`、`dsh_wave.py`、`s_userleft.py` |
| 配色 | `tuikit.py`（调色板）、`seg.html` + `build_frame.py`（主题变量） |

## 用法

```bash
git clone https://github.com/MisakaZentai/world-execute-me-dsh-pv.git
cd world-execute-me-dsh-pv
git apply /path/to/2026-11-08-达妮娅改造.patch
# 之后按 docs/07-macOS复刻说明.md 装配环境
```

补丁已在原作者仓库的 master（`a598092`）上验证可干净应用。

## 注意

- 补丁**不含**素材（插画、字体、歌曲）与生成物（截图、成片），那些按文档自行准备。
- 上游若已更新，补丁可能需要手动 rebase。
