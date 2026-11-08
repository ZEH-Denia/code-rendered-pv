# 坑清单（动手前必读）

> 这些不是理论，是同一单活里逐条撞出来的。每一条都附「怎么查」。

---

## 一、坐标系：同一概念、多处常量

渲染一支角色 PV，至少四套坐标各自成立：

| 位置 | 形态 | 例子 |
|---|---|---|
| 立绘文件 | 935×1682 RGBA 画布 | `whale-star.webp` |
| 窗口头像 | 固定像素框 | `crop((250, 40, 690, 480))` |
| TUI 精灵 | 比例裁剪 | `CROPS = {"face": (0.20, 0.0, 0.78, 0.26)}` |
| 舞台缓存 | 420×540 像素框 | `{"face": (80, 80, 335, 250)}` |
| 特写 | 虹膜坐标 + 倾角 | `EYES = ((211.3, 216.3), (292.5, 196.3))` |

**换素材时这些必须全部重测**，否则会出现「改完看着对、某个镜头却裁到发顶」。

### 怎么查

```bash
# 全工程搜裁剪与坐标常量
grep -rn "crop((\|CROP *=\|EYES\|boxes *=\|getbbox" --include=*.py .
# 逐个渲染确认
python -c "import tuikit as t; t.sprite_src('cheerful','face').save('/tmp/c.png')"
```

### 怎么定

1. 把新素材按**原素材的画布比例**摆进去（头顶贴 y=0、宽度吃满 68%、水平居中）。
2. 用带坐标网格的预览图确定特征点（眼睛、嘴、下巴），再换算回各套坐标系。
3. 每改一套，单独渲一帧验证，别一次全改。

---

## 二、渲染期的模块替换

`sprite_src` 这类函数可能在**渲染进程里被别的模块顶替**：

```
tuikit.sprite_src        读立绘 webp
        ↓ 运行时被替换
h3_full.sprite_src       读缓存帧（420×540）
```

你改的是 tuikit 的调用，实际生效的是 h3_full 的常量——**改了等于没改**。

### 怎么查

```bash
grep -rn "replace_alias\|\.sprite_src *=\|install(sys.modules" --include=*.py .
```

并且注意：渲染进程里通常有**文件守卫**（禁止直接打开角色素材），所以「绕过被替换的函数、自己 open 文件」会直接报错。正确做法是改那套被替换函数的常量。

---

## 三、文字烤进截图 vs 实时绘制

| 画面侧 | 实现 | 改文案后的代价 |
|---|---|---|
| 网页窗（左半屏） | HTML → Playwright 截图 | **必须重跑全部截图**（4968 张 ≈ 400 s） |
| TUI（右半屏） | PIL 逐帧画 | 只需重渲染（60–250 s） |

只看不出的后果：以为改完了，成片里窗内还是旧字。

### 怎么查

```bash
# 生成页面里的文本是权威（截图就是它）
for k in 旧词1 旧词2; do echo "$k: $(grep -o "$k" *_frames.json | wc -l)"; done
```

---

## 四、配色：三种写法并存

1. **十六进制** `#4d6bfe`（CSS / 内联样式）
2. **RGB 元组** `(120, 150, 255)`（PIL colorize）
3. **通道斜坡** `(int(10+70*v), int(16+90*v), int(40+215*v))`（生成噪点头像之类）

只改前两种，第三种会让某个角落仍是旧色。**必须用像素统计验证**：

```python
blue = ((b > r+30) & bright).sum() / total    # 目标：0 帧超阈值
```

### 辉光补偿

成片里的小面积高饱和元素会被 bloom 提亮：设计值 `#B0567E` 实测成 `(205,104,149)`。
**要"不抢眼"就往目标再压一档**（本次最终用 `#8E4A6B`，实测 `(168,91,129)`）。

### 对比度校验

改色后算 WCAG 对比度，确保没降低可读性：

```python
def cr(a, b):  # a/b 为 (r,g,b)
    def lum(c):
        f = lambda v: (v/255)/12.92 if v/255 <= 0.03928 else (((v/255)+0.055)/1.055)**2.4
        r, g, bl = (f(x) for x in c)
        return 0.2126*r + 0.7152*g + 0.0722*bl
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)
```

目标是 ≥4.5:1（正文）、≥3:1（大字与图形）。

---

## 五、音频对齐

不同来源的同一首歌会整体早/晚几十毫秒，**24 fps 下一帧 = 41.7 ms**。

- **量**：用参考包络做瞬态互配（`scripts/check_song_alignment.py`），别用肉耳。
- **修**：`atrim=start=0.127,asetpts=PTS-STARTPTS,apad=whole_dur=211.913`——裁头 + 补尾，保持总长不变。
- **必查**：`-shortest` 会用较短的那条流截断输出。音轨短了，片尾就被削掉。

---

## 六、编码与封装

| 现象 | 原因 | 处置 |
|---|---|---|
| 成片比预期短 | `-shortest` + 音轨短 | 补尾对齐总时长 |
| 4K 看着糊 | 用了插值放大 | 像素画用 `flags=neighbor`，只做整数倍 |
| 安卓/网页不认 HEVC | 少了 hvc1 tag | `-tag:v hvc1` |
| 颜色发灰 | 没写色彩标记 | `-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv` |
| ffmpeg 9 报 `Unrecognized option 'vsync'` | 已移除 | 改 `-fps_mode` |

---

## 七、平台与字体

- 系统 python 常是 3.9，跑不动 3.12+ 的工程；`uv venv --python 3.12` 最省事。
- Windows 字体（Consolas / 微软雅黑 / Segoe UI Symbol）在别的系统不存在，**用环境变量覆盖**，不要改源码里的默认值。
- 换字体必然改变字宽（Consolas 0.55 em vs 常见等宽 0.6 em，宽约 9%），逐字符网格排版会轻微错位——这是既知代价，写在交付说明里。
- Playwright 1.49 起 headless 默认走 `chromium-headless-shell`，字体渲染路径与本机 Chrome 不同，**逐帧截图必须固定用同一个浏览器**。
