<div align="center">

# fig-check

**按论文印出来的样子检查图。** 文字按印刷大小量（算上图在论文里的缩放），找出色觉异常读者分不清的颜色，以及印刷时太粗糙的位图；
LaTeX 工程里的每张图都按它实际印出的宽度检查。

<a href="https://github.com/zch6a/fig-check/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zch6a/fig-check/actions/workflows/ci.yml/badge.svg"></a>
<img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
<img alt="No dependencies" src="https://img.shields.io/badge/dependencies-none-2ea44f">
<a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue"></a>

[English](README.md) · **简体中文**

</div>

---

一张图按 6 英寸宽、10 pt 标签画出来，放进 3.25 英寸的栏里，标签就只剩 5.4 pt。红线和绿线在大约十二分之一的北欧裔男性看来是同一条线。
640 像素宽的图拉满正文宽度，印出来每英寸只有 116 个像素。这些在屏幕上放大看都发现不了；fig-check 在审稿人之前找出来。

```bash
uvx --from git+https://github.com/zch6a/fig-check fig-check paper/
```

输出示例见[英文 README](README.md)（对 [examples/paper](examples/paper) 这个虚构工程运行的结果）。没有问题时退出码为 0，有问题为 1，无法运行为 2；`--json` 输出各工程所用的宽度及其来源，以及每张图的检查结果。只读本地文件，不联网。要用 Python 接口时安装：`pip install git+https://github.com/zch6a/fig-check`。

## 读取什么

- **LaTeX 工程**（文件夹或主 `.tex`）：每个 `\includegraphics`，跟随 `\input` 与 `\include`，按印出的宽度计算：`width=`、`height=`、`scale=`、`\resizebox`，
  以及 `figure`（栏宽）、`figure*`（正文宽）、`wrapfigure`、`subfigure`、`minipage` 里的行宽。会议的宽度取自导言区加载的样式文件，或按 LaTeX `article` 的规则由文档类选项（`11pt`、`a4paper`、`twocolumn`）算出；
  再应用导言区自己的 `geometry` 选项、`\setlength{\textwidth}` 或 `\columnsep`。识别不了时用 `--template` 指定。
- **单张图**：`fig-check plot.pdf --width 3.25in`。
- **按印出的宽度做图**：在 `plt.rc_context(paper_style("icml"))` 里画图，再用 `save_for_paper(fig, "figures/loss.pdf", "icml")` 保存。图按会议的栏宽（ICML 为 3.25 英寸）做，字体用论文的字体（NeurIPS、ICLR、ICML、CVPR、ACL 用 Times，`article` 用 Computer Modern），坐标轴标签比正文小 1 pt、刻度小 2 pt；保存时宽度正好等于栏宽，字体以 TrueType 嵌入（不是 Type 3），保存后立即按这个宽度检查。论文里 `\includegraphics[width=\columnwidth]` 插入时缩放比例为 100%，字印出来就是做图时的字号。`bbox_inches="tight"` 会改变宽度，`save_for_paper` 不接受；论文用 Times 而图里没有 Times 时会给警告（没装 Times 字体时 matplotlib 会退回 DejaVu）。
  字体和字号是 pdflatex 加载各会议样式文件后实际设置的值（在 `\begin{document}` 之后打印 `\f@family` 和 `\f@size`）：NeurIPS、ICML、ICLR 为 Times 10 pt，ACL 为 Times 10.95 pt；`cvpr.sty` 在这里编译不了（缺 `silence.sty`），它加载 `times`，模板是 `10pt`。其他模板请传 `font="times"` 或 `font="computer modern"`。端到端实测：用 `paper_style("icml")` 做的图，以 `\columnwidth` 插入用 `icml2025.sty` 编译的论文（栏宽 234.88 pt = 3.25 英寸），fig-check 检查结果为缩放 100%、最小字号 8 pt。
- **让 LaTeX 来画**：`save_pgfplots(fig, "figures/loss.tex")` 把 matplotlib 图写成 pgfplots 代码，论文里 `\input` 它（导言区加 `\usepackage{pgfplots}`），
  LaTeX 按印出的宽度、用论文自己的字体和字号画图，字就不会随图缩小（端到端实测：同一张 6×4 英寸的图放进双栏论文，作为 PDF 插入时字印出 5.3 pt，导出为 pgfplots 后为 10 pt）。导出折线、散点、柱、`fill_between`、误差棒、文字、坐标轴标签、标题、范围、对数轴、刻度、网格、图例；
  不能导出的（图像、色条、3D、整图文字）在返回的 notes 里列出，也写在文件开头的注释里。
- **会议之外的文档类**：IEEEtran、acmart（sigconf 等）、llncs、elsarticle、revtex4-2 的宽度是 pdflatex 用这些类与选项实际排出来的结果。
- **保存之前的 matplotlib 图**：`check_figure(fig, width="column", template="icml")`，返回的报告 `print()` 出来与命令行输出相同；图只在内存里存成 PDF 检查，不写盘，其余关键字参数传给 `savefig`。
- **格式**：PDF（只用标准库读取：文字、颜色、内嵌图片、表单 XObject、压缩流与对象流）、PNG（解码取颜色）、JPEG（取尺寸）、SVG。EPS 只提示，不读取。

支持的模板（NeurIPS、ICLR、ICML、CVPR/ICCV、ACL/EMNLP/NAACL、AAAI）及其宽度见英文 README 的表格，每一项都是 2026-11-13 从样式文件本身读出的。
由文档类选项与 `geometry` 算出的宽度按 `article.cls`、`size1x.clo`、`geometry.sty` 的规则计算；33 种导言区写法（纸张、页边距、只给一侧页边距、`twoside`、`landscape`、双栏、`\setlength`、`\addtolength`）与 pdflatex 实际排出的宽度一致（误差 0.01 pt 内），测试里固定了这些宽度。

## 检查什么

- **印刷后的字号**：图里每一段文字，按画出的大小乘以图在论文中的缩放。小于 7 pt 为警告，小于 5 pt 为错误（`--min-font`）。Elsevier 的经验规则是正常文字印出后 7 pt、上下标不小于 6 pt。
- **色觉异常**：图中用到的每一对颜色，正常视觉下明显不同（CIEDE2000 ΔE ≥ 15），而在红色盲、绿色盲或蓝色盲下几乎一样（ΔE < 6），按 Machado、Oliveira 与 Fernandes（2009，严重程度 1）的矩阵模拟。灰色不计；颜色很多的图视为色图，只给建议。
- **分辨率**：位图以及 PDF 里内嵌的位图，按每印刷英寸的像素数。小于 300 为警告，小于 150 为错误（`--min-dpi`）。IEEE 要求彩色与灰度图大于 300 dpi，Elsevier 要求半色调图 300 dpi。没写分辨率的 PNG 按 72 dpi 算，与 pdfLaTeX 一致。

色彩计算按原始资料校验：CIEDE2000 用 Sharma、Wu 与 Dalal 的全部 34 组测试数据，模拟矩阵与作者公布的表格逐位一致。

## 局限

- 不认识的样式文件或文档类（如 memoir、未测量的 acmart 格式）不读取：会提示并按 `article` 计算；请用 `--template`，或用 `--width` 单独检查图。写在宏里、或用 `\setlength`/`\addtolength` 以外的运算设置的宽度不跟随。
- 由宏拼出的路径（`\iftoggle{hq}{a}{b}`）只计数，不跟随。
- 转成轮廓（路径而非字体）的文字不算文字；位图里的文字也量不了。
- 颜色取路径与文字的颜色；渐变与图案不跟随。

## 属于 research-kit

这是 13 个开源科研工具之一，覆盖从读论文到论文发表之后。全部工具按科研流程的介绍，以及安装它们技能的 Claude Code 插件市场，见 [research-kit](https://github.com/zch6a/research-kit) · [网站](https://zch6a.github.io/research-kit/)。

## 许可证

MIT。
