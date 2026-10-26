# `test` 书写动画：原理与做法

## 苹果怎么做的

macOS 27 欢迎屏的 "hello" 由私有字体 `MacintoshSkeletal.otf` 驱动，位置：

```
/System/Library/PrivateFrameworks/SetupAssistantSupportUI.framework/Versions/A/Resources/
```

本机用 fontTools 打开核实过：它有普通的 `CFF/GSUB/GPOS`，外加一张私有表 `strk`（JSON，约 2.7 MB）。笔顺信息就在这张表里，而不在轮廓里：

- 每个字形是一组 `strokes`，**数组顺序就是落笔顺序**。
- 每个点是 `[x, y, z, r]`，单位 em，`r` 是笔尖半径（约 0.034 em）。社区逆向（jhao941/McIntosh-Writer）认为这些点是均匀三次 B 样条控制点，渲染器沿中心线按半径把它“管状化”成笔画。
- `deferred: "Next Break"` 标记的笔画（`t` 的横、`i` 的点）不跟着写，**推迟到当前词写完再补**，和真人写连笔字一样。
- `info.joinsForward / joinsBackward`、`start/end.target`、`Final Attachment Anchor` 控制字母之间怎么接；具体选哪个变体（`t.initial`、`e.midEntry` 等）和插哪段桥接，由 GSUB 的 `calt/rlig` 决定。

本机看到的 `t` / `e` / `s` 笔画：

| 字形 | 笔画（类型, deferred, 点数） |
|---|---|
| t | Open/Not/5, **Open/Next Break/2**（横）, Open/Not/8 |
| e | Open/Not/18 |
| s | Open/Not/6, Open/Not/8, Open/Not/5 |

字体只给几何和笔顺。笔速、渐变色、光晕属于应用层，苹果没有公开，下面这些参数都是近似还原。

## 这里怎么做的

渲染器读不了 `strk`，所以用目录里社区重建的 `MacintoshSkeletalVariable.otf`（npwitk/Macintosh-Skeletal-Filled，就是把 `strk` 转成普通轮廓）：

1. **整形**：`hb-shape` 跑一遍 `test`，拿到带连笔变体和桥接字形的序列，和系统排版结果一致。
2. **取回中心线**：Variable 版本里每个轮廓就是一笔，即中心线向两侧各偏移半个笔宽，笔宽随 `wght` 线性变化。在 `wght` 100 和 500 两个母版之间外推到笔宽 = 0，闭合轮廓会塌回中心线（走过去再走回来）。取前一半弧长就是笔画路径，起点就是落笔点。
3. **还原笔顺**：首尾相接的笔画串成一条（距离 < 400 单位），这就是连写的主体；接不上的（`t` 的两道横）放到最后从左到右补写，等价于 `strk` 的 `Next Break` 规则。
4. **动画**（`template.html`，纯 SVG + JS，没有依赖）：
   - 每笔一条 `<path>`，用 `stroke-dasharray/offset` 逐步显露，圆头圆角。
   - 笔速遵循手写的 2/3 幂律：速度 ∝ 曲率^(-1/3)，弯道慢、直线快。每笔预先算一张“时间 → 弧长”表。
   - 每段落笔整体再套一层缓动（35% 线性 + 65% smoothstep），起笔有加速、收笔轻落，中途不会停顿。
   - 提笔补横前停 0.16 s，全程约 3.3 s。
   - 横向渐变（蓝 → 紫 → 粉 → 橙）加柔和的 `drop-shadow` 光晕，跟随系统深浅色。
   - 长度为 0 时隐藏路径，避免圆头先冒出一个点；`prefers-reduced-motion` 时直接显示成品。

## 使用

```sh
python3 -I build.py test    # 需要 fontTools、hb-shape（brew install harfbuzz）
open test.html              # 点“重播”再看一次；?t=0.5 定格在 50%（截图检查用）
```

换别的词：`python3 -I build.py hello` 会生成 `hello.html`。

## 局限

- 笔宽恒定。`strk` 里每个点自带半径（如 `t` 的 0.034 → 0.032），原版有轻微粗细变化，这里没做。要做的话直接解析 `strk`，按半径逐段描边。
- 笔顺靠端点距离推断，不是直接读 `strk` 的数组顺序。`test` 已截图逐帧核对过（t → e → s → t，最后补两道横），换成笔画复杂的词可能需要改成直接读 `strk`。

## 来源

- 系统字体 `strk` 表：本机直接读取（上文路径）
- 逆向与浏览器复刻：https://github.com/jhao941/McIntosh-Writer
- Filled/Variable 重建字体：https://github.com/npwitk/Macintosh-Skeletal-Filled
- 早期 SVG trim 方案（不基于该字体）：https://github.com/mtynior/AppleHello
