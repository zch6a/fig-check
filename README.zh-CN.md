<div align="center">

# fig-check

**按论文印出来的样子检查图。** 文字按印刷大小量（算上图在论文里的缩放），找出色觉异常的读者分不清的颜色，以及印刷时太粗糙的位图；
LaTeX 工程里的每张图都按它实际印出的宽度检查。

<a href="https://github.com/zch6a/fig-check/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zch6a/fig-check/actions/workflows/ci.yml/badge.svg"></a>
<img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
<img alt="No dependencies" src="https://img.shields.io/badge/dependencies-none-2ea44f">
<a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue"></a>

[English](README.md) · **简体中文**

</div>

---

一张图按 6 英寸宽、10 pt 标签画出来，放进 3.25 英寸的栏里，标签就只剩 5.4 pt；红线和绿线在大约十二分之一的男性看来是同一条线；
640 像素宽的图拉满正文宽度，印出来每英寸只有 116 个像素。这些在屏幕上放大看都发现不了；fig-check 在审稿人之前找出来。

```bash
uvx --from git+https://github.com/zch6a/fig-check fig-check paper/
```

输出示例见[英文 README](README.md)（对 [examples/paper](examples/paper) 这个虚构工程运行的结果）。没有问题时退出码为 0，有问题为 1，无法运行为 2；`--json` 输出报告。

## 读取什么

- **LaTeX 工程**（文件夹或主 `.tex`）：每个 `\includegraphics`，跟随 `\input` 与 `\include`，按印出的宽度计算：`width=`、`height=`、`scale=`、`\resizebox`，
  以及 `figure`（栏宽）、`figure*`（正文宽）、`wrapfigure`、`subfigure`、`minipage` 里的行宽。会议的宽度取自导言区加载的样式文件，或按 LaTeX `article` 的规则由文档类选项（`11pt`、`a4paper`、`twocolumn`）算出；
  再应用导言区自己的 `geometry` 选项、`\setlength{\textwidth}` 或 `\columnsep`。识别不了时用 `--template` 指定。
- **单张图**：`fig-check plot.pdf --width 3.25in`。
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

- 不认识的样式文件或文档类（IEEEtran、acmart、revtex、llncs 等）不读取：会提示并按 `article` 计算；请用 `--template`，或用 `--width` 单独检查图。写在宏里、或用 `\setlength`/`\addtolength` 以外的运算设置的宽度不跟随。
- 由宏拼出的路径（`\iftoggle{hq}{a}{b}`）只计数，不跟随。
- 转成轮廓（路径而非字体）的文字不算文字；位图里的文字也量不了。
- 颜色取路径与文字的颜色；渐变与图案不跟随。

## 许可证

MIT。
