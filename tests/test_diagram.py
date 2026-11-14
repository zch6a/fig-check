"""diagram() on stand-in modules (anything with named_children and parameters; no torch needed)."""

from __future__ import annotations

from fig_check import diagram


class P:
    def __init__(self, n: int) -> None:
        self.n = n

    def numel(self) -> int:
        return self.n


class M:
    def __init__(self, own: int = 0, **children: M) -> None:
        self._own, self._children = own, children

    def named_children(self):
        return list(self._children.items())

    def parameters(self):
        yield P(self._own)
        for c in self._children.values():
            yield from c.parameters()


class Conv2d(M): ...


class ReLU(M): ...


class Linear(M): ...


class Block(M): ...


class Sequential(M): ...


class Dropout(M): ...


class Encoder(M): ...


class Net(M): ...


def block(down: bool = False) -> Block:
    return Block(0, conv=Conv2d(100), relu=ReLU(), **({"down": Conv2d(10)} if down else {}))


def test_stages_collapse_and_labels():
    net = Net(conv1=Conv2d(9408), relu=ReLU(), layer1=Sequential(**{"0": block(), "1": block()}),
              layer2=Sequential(**{"0": block(down=True), "1": block()}), drop=Dropout(), fc=Linear(513000))  # fmt: skip
    d = diagram(net, skip=("Dropout",))
    labels = [d._label(b) for b in d.blocks]
    assert labels == [("Conv2d", "conv1, 9.4K"), ("ReLU", ""), ("Block ×2", "layer1, 200"), ("Block ×2", "layer2, 210"), ("Linear", "fc, 513.0K")]
    tikz = d.tikz()
    assert tikz.count("\\node[block") == 5 and tikz.count("\\draw[arrow]") == 4 and "Block $\\times$2" in tikz
    assert "positioning" in tikz and "·" not in tikz  # a middle dot makes pdflatex use a bitmap font
    renamed = diagram(net, labels={"layer1": "Stage 1"}, skip=("Dropout",))
    assert renamed._label(renamed.blocks[2]) == ("Stage 1 ×2", "200")


def test_nested_containers_and_rows():
    layers = Sequential(**{str(i): Block(1000, attn=Linear(800), mlp=Linear(200)) for i in range(12)})
    vit = Net(proj=Conv2d(590), encoder=Encoder(0, drop=Dropout(), layers=layers, norm=Linear(2)), head=Linear(769))
    d = diagram(vit, depth=2, skip=("Dropout",))
    enc = d.blocks[1]
    assert d._inner(enc) == ["Block ×12", "Linear"]  # encoder.layers opened: its 12 blocks, not one "Sequential"
    wrapped = diagram(Net(**{f"l{i}": Linear(i + 1) for i in range(7)}), per_row=3)
    t = wrapped.tikz()
    assert "below=0.6cm of b0" in t and "below=0.6cm of b3" in t and t.count("-| (b") == 2
    svg = wrapped.svg()
    assert svg.startswith("<svg") and svg.count("<rect") == 7 and svg.count("<polyline") == 2
    seq = diagram(Sequential(**{"0": Linear(40), "1": ReLU(), "2": Linear(18)}))
    assert [b.kind for b in seq.blocks] == ["Linear", "ReLU", "Linear"]  # an nn.Sequential model: its layers
