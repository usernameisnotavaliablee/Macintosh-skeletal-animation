# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

复刻 macOS 27 欢迎屏 "hello" 的手写书写动画。输入一个词,`build.py` 用社区重建字体 `MacintoshSkeletalVariable.otf` 还原笔画中心线与笔顺,生成一个自包含的 HTML(纯 SVG + JS,无依赖)。原理、参数取舍和局限见 `README.md`,改动前先读。

## 常用命令

```sh
python3 -I build.py test    # 生成 test.html;依赖 fontTools 和 hb-shape(brew install harfbuzz)
python3 -I build.py hello   # 任意词,输出 <词>.html
open test.html              # 浏览器预览;?t=0.5 定格在时间线 50%,用于截图核对
```

- `build.py` 用相对路径读取 `MacintoshSkeletalVariable.otf` 和 `template.html`,必须在仓库根目录运行。
- 没有测试和 lint。验证方式是生成后用 `?t=` 参数截图逐帧核对笔顺。

## 架构

流水线分两段,跨 `build.py` 和 `template.html`:

1. **`build.py`(离线)**:`hb-shape` 整形得到连笔变体和桥接字形 → 在 `wght` 100 与 500 两个母版间外推到笔宽 0,闭合轮廓塌成中心线,取前半弧长作为笔画路径 → 按端点距离(阈值 400 单位)贪心串联成书写顺序,串不上的(`t` 的横、`i` 的点)排在最后从左到右补写 → 输出 SVG 路径数据 `{paths, lift, width, box}`。
2. **`template.html`(运行时)**:`build.py` 把 JSON 替换进模板里的占位符 `/*DATA*/null`。模板按 2/3 幂律(速度 ∝ 曲率^(-1/3))为每笔预算“时间 → 弧长”表,再用 `stroke-dasharray/offset` 显露。`DATA.lift` 是第一笔“抬笔”补写笔画的下标,之前是连写主体,之后每笔单独成块。

## Git 工作方式

- 不使用 worktree 和额外分支:直接在 `main` 上工作和提交,不要调用 EnterWorktree 或新建分支。
- 推送 `main` 前先询问用户。

## 注意事项

- 模板占位符 `/*DATA*/null` 必须原样保留,否则 `build.py` 替换不到数据。
- 模板里的 `<title>` 和 `aria-label` 写死为 `test`,生成其他词时不会自动改。
- 笔宽恒定,笔顺由端点距离推断而非直接读 `strk` 表;换笔画复杂的词可能需要改这两处(README「局限」一节)。
- `test.html`、`hello.html`、`hzyyyyy.html` 是生成产物,改行为应改 `build.py` 或 `template.html` 后重新生成。
- 两个 `.otf` 文件体积大(约 6 MB 和 55 MB),不要重复提交或改名。
- 目录 `dsh-swe制作效果-其他Agent不要读/` 按用户标注不读取、不修改。
