# Apple "hello" 书写动画 × Macintosh Skeletal 字体 — 机制与复刻

本目录演示：用 `test` 字样复刻 Apple macOS "Hello" 屏保 / Setup Assistant 的手写体书写动画。

- 打开方式：直接双击 `index.html` 即可跑（动画数据已内嵌，JS 无依赖）。字体对照层需要同目录的
  `MacintoshSkeletalFilled.otf`；浏览器 file:// 下可能拦截本地字体加载，此时可在本目录起
  `python3 -m http.server 8766` 再访问。

---

## 一、Apple 是怎么做的（一手证据）

### 1. 数据：书写顺序是「数据」，不是「猜」

Apple 的真字体 `MacintoshSkeletal.otf`（2.86MB，静态 CFF）藏在：

    /System/Library/PrivateFrameworks/SetupAssistantSupportUI.framework/Versions/A/Resources/

它内含一张 **Apple 私有 `strk` 表 —— 2.7MB，整个表就是一份 JSON**（fontTools 不认识，
用 `getTableData("strk")` 读出来直接 `json.loads`）。结构：

```json
{"glyphOrder": [1828 个字形名],
 "glyphs": {
   "t": {
     "info": {"deferJoining": false, "joinsForward": 2, "joinsBackward": 0,
              "joiningOptionalForward": false, "optionalForwardKerning": 50},
     "strokes": [
       {"type": "Open", "points": [[x,y,z,r], ...],           // 均匀三次 B 样条控制点
        "info": {"start": {"cap":"round","tangency":0},
                 "end":   {"cap":"round","tangency":1,"injector":true,
                           "snappingTarget":2,"snappingPriority":0}}},
       {"type": "Open", "info": {"deferred":"Next Break", ...}},   // t 的横画 = 延后笔划
       {"type": "Final Attachment Anchor", "points": [[x,y,z,r]]}  // 下一字母附着锚点
     ]}}}
```

- `strokes` 数组顺序 **= 书写顺序**（t 有 4 项：3 笔 + 1 个附着锚点）
- 每笔 `points` = **中轴线的均匀三次 B 样条控制点**，每点 `[x,y,z,r]`：
  x/y/z 是 3D 位置（em 归一化），**r = 该点笔半径**（逐点笔压）
- 笔划类型：`Open`(4842) / `Closed`(86，闭环如 o) / `Dot`(108，点) / `Final Attachment Anchor`(271)
- 端点元数据管「怎么连笔」：`injector`（笔尖注入下一笔）、`snappingTarget/Priority`（吸附目标/优先级）、
  `tangency`（切向要求）、`deferred:"Next Break"`（延后到下一个断点再写——t 的横画就是如此）
- `joinsForward/Backward`、`optionalKerning` = 字母间连写/字距规则

**运行时连笔不在字体里**：字母与字母之间的连接笔迹由 Apple 渲染器按 injector/snapping/锚点规则
实时生成。npwitk 复刻字体时从 iOS Simulator 渲染器录制了约 14000 对字母连接，烘焙成字体里的
零宽 `_br.*` 连接字形。

### 2. 烘焙产物：每语言一份 strokes JSON

macOS Sonoma+ 的屏保本体（Big Sur 时代叫 `Hello.saver`，现为壁纸+屏保一体）：

    /System/Library/ExtensionKit/Extensions/Hello.appex/Contents/Resources/Languages/*.json

38 种语言各一份，内部字体名 `Macintosh 3D`，`strokes` = 按书写顺序的笔划数组，
每笔 = 三次贝塞尔段 `{p0,p1,p2,p3}`，**每点 `[x,y,z,width]`**。en "hello" 只 2 笔（提笔 1 次），
zh_CN "你好" 9 笔。Setup Assistant 的 `HelloText/*.json` 同构。这些 JSON 只覆盖 "hello" 一词，
不是完整字母表。

### 3. 渲染：SceneKit + shader modifier（二进制里能读到 shader 源码）

`Hello.appex` 可执行文件（Swift）内嵌三段 Metal shader，经 `setShaderModifiers:` 注入 SceneKit：

```glsl
// (a) 书写揭示 fragment —— position uniform 沿全词累计弧长推进，超前 discard
if (in.linePosition > position && animate == 1.0) discard_fragment();

// (b) 笔锋生长 vertex —— 圆管在写入点之后滞后 rampTime 膨胀 → "落笔细→变粗"
_geometry.position.xyz -= _geometry.normal * info.y
    * smoothstep(positionMinusRampTime, position, info.x) * weightChange;

// (c) 彩虹渐变 fragment —— 世界坐标 X 映射 hue
```

数据流：`strokes 中轴线 + 逐点半径 → 扫掠成 3D 圆管网格 → 每顶点记 linePosition(累计弧长)
→ position uniform 逐帧扫描 → 未写到的位置整段 discard`。`penNode` 笔尖模型沿路径走；
相机动画有 `rotateFull/panFront/straightDown` 等枚举（"Macintosh 3D" 之名来自真 3D 立体管）。
动画类型枚举叫 `TextAnimationType.writeIn`。

### 4. `wght` 可变轴与动画无关

wght 只缩放笔半径（Apple 常量：存储半径 ×1.55 = 屏上粗细；npwitk 复刻字体
100≈0.6×、500≈1.55×、900≈2.5×）。**书写进度是渲染器 uniform，不在字体文件里。**

---

## 二、本目录的复刻

工作区两份 otf 是 **npwitk 的复刻字体**（非 Apple 原件）。npwitk 已把 strk 数据烘焙成字形轮廓——
每个字形的每条闭合轮廓 = 一条笔迹的"管壁"（ribbon），连笔已烘成零宽 `_br.*` 字形。
所以不必解析 strk，直接从轮廓反推笔迹即可。

### 提取（extract.py → strokes.json）

1. **uharfbuzz 排版** "test" → GSUB 选中上下文变体：
   `t.initial.cT _br.13552 e.cHT _br.7460 s.cHT _br.13241 t.final.cH`
   （两份字体 GID/advance 完全一致，14 条轮廓 = 14 笔）
2. **轮廓 = 绕笔迹一圈的细条**：从落笔点沿一侧管壁走到笔锋（≈总弧长一半处），再沿另一侧回到起点。
   按弧长对半切开 = 两条边 edge1/edge2。
3. 两边各按弧长重采样 160 点 → 输出 `{e1, e2, len}`（len = 笔迹弧长，用于定时）。
4. **笔顺**：轮廓顺序 ≠ 书写顺序（t 的轮廓顺序是[入笔,横画,竖干,提钩]）。
   按端点连通性重排为 `0→3→2→1 | 4→5 | 6→7→8 | 9→10→13→12→11`，
   横画排在每个 t 主干之后 —— 正对应 strk 里 `deferred:"Next Break"` 的语义。

### 动画（index.html，单文件，无依赖）

对每笔 `{e1,e2}`，进度 p → 画**前缀多边形** `e1[0..m] + 反序 e2[0..m]`
（m = p×160，末端线性插值）。即两条管壁等速推进、笔锋处闭合——视觉上笔迹被“写出来”，
等效于 Apple 的 `linePosition > position → discard`，只是方向反过来（只画已写部分）。

与 Apple 渲染的三处对齐：
- **宽度 ramp**（等效其 vertex shader 的 `smoothstep(positionMinusRampTime, position, …)`）：
  刚写到的部分向中轴收拢变细、0.28s 内长到全宽 → 落笔细→变粗的墨迹感；
- **圆头笔尖**：白点贴在中轴前端、半径=该处管宽×1.05（封顶 65 单位），兼作 cap:"round"；
- **连笔不抬笔**：相邻笔划端点间距 <80 单位则不插停顿（连写一气呵成），真正断笔处
  才给 100ms 提顿 + 白点弧线路径飞向下笔点。
速度 ∝ 笔迹弧长（3400 units/s），全程约 8.3s。彩虹默认开，linearGradient 用
userSpaceOnUse 横跨整个词（对应 Apple spectrum 主题的 worldX→hue）。


### 与 Apple 的差异（诚实清单）

| | Apple | 本演示 |
|---|---|---|
| 笔迹源 | strk B样条中轴+半径（真3D，有 z） | 复刻字体的烘焙轮廓（2D） |
| 揭示 | fragment discard 按累计弧长 | 前缀多边形逐帧重建 |
| 笔锋 | smoothstep 宽度 ramp | 有（向中轴收拢 0.28s） |
| 连笔 | 引擎按 injector/snapping 实时生成 | 复刻字体已烘死 |
| 相机 | 3D 旋转/pan | 无 |

---

## 三、文件

- `index.html` — 动画本体（内嵌 strokes.json，~82KB，JS 无依赖）
- `extract.py` — 提取脚本（fontTools + uharfbuzz；`.venv` 内 `python extract.py` 重跑）
- `strokes.json` — 14 笔的双边点列数据
- `debug_*.png` / `frames.png` — 过程验证图
- `MacintoshSkeletalVariable.otf` / `MacintoshSkeletalFilled.otf` — npwitk 复刻字体（数据源+对照层）

## 四、换别的词

改 `extract.py` 顶部 `TEXT`，重跑生成 strokes.json，再把数据重新内嵌进 index.html 即可。
注意：笔顺连通性规则对小写连写字母通用，但大写/数字需检查 `Final Attachment Anchor` 与
deferred 笔划的语义。

## 来源

- https://github.com/npwitk/Macintosh-Skeletal-Filled （复刻字体 + strk 逆向 + 1.55× 半径常数）
- https://github.com/jhao941/McIntosh-Writer （唯一公开读 strk 表的工具；apple-extract.py 记录 strk 语义：oncurve=false 影子点只定方向、屏宽=半径×2×1.55、deferred 笔划在抬笔时补）
- https://github.com/gkurt/tegaki （通用“任意字体→书写动画”路线参照）
- https://github.com/LiYanan2004/HelloScript （SwiftUI 复刻，子路径=笔序）
- https://github.com/mtynior/AppleHello + https://thisdevbrain.com/apple-hello-animation/
- https://www.trapti.dev/the-desk/3d-text-line-animation-using-greensock-and-svg/
- 本机一手证据：`Hello.appex/Contents/Resources/Languages/*.json`、其二进制内嵌 SceneKit
  shader modifier 源码、`MacintoshSkeletal.otf` 的 `strk` JSON 表
