"""The colour science against its sources."""

from __future__ import annotations

import pytest

from fig_check.color import MACHADO, ciede2000, clashes, simulate

# Sharma, Wu and Dalal (2005), the CIEDE2000 test data published with the paper:
# https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/dataNprograms/ciede2000testdata.txt
SHARMA = """
50.0000 2.6772 -79.7751 50.0000 0.0000 -82.7485 2.0425
50.0000 3.1571 -77.2803 50.0000 0.0000 -82.7485 2.8615
50.0000 2.8361 -74.0200 50.0000 0.0000 -82.7485 3.4412
50.0000 -1.3802 -84.2814 50.0000 0.0000 -82.7485 1.0000
50.0000 -1.1848 -84.8006 50.0000 0.0000 -82.7485 1.0000
50.0000 -0.9009 -85.5211 50.0000 0.0000 -82.7485 1.0000
50.0000 0.0000 0.0000 50.0000 -1.0000 2.0000 2.3669
50.0000 -1.0000 2.0000 50.0000 0.0000 0.0000 2.3669
50.0000 2.4900 -0.0010 50.0000 -2.4900 0.0009 7.1792
50.0000 2.4900 -0.0010 50.0000 -2.4900 0.0010 7.1792
50.0000 2.4900 -0.0010 50.0000 -2.4900 0.0011 7.2195
50.0000 2.4900 -0.0010 50.0000 -2.4900 0.0012 7.2195
50.0000 -0.0010 2.4900 50.0000 0.0009 -2.4900 4.8045
50.0000 -0.0010 2.4900 50.0000 0.0010 -2.4900 4.8045
50.0000 -0.0010 2.4900 50.0000 0.0011 -2.4900 4.7461
50.0000 2.5000 0.0000 50.0000 0.0000 -2.5000 4.3065
50.0000 2.5000 0.0000 73.0000 25.0000 -18.0000 27.1492
50.0000 2.5000 0.0000 61.0000 -5.0000 29.0000 22.8977
50.0000 2.5000 0.0000 56.0000 -27.0000 -3.0000 31.9030
50.0000 2.5000 0.0000 58.0000 24.0000 15.0000 19.4535
50.0000 2.5000 0.0000 50.0000 3.1736 0.5854 1.0000
50.0000 2.5000 0.0000 50.0000 3.2972 0.0000 1.0000
50.0000 2.5000 0.0000 50.0000 1.8634 0.5757 1.0000
50.0000 2.5000 0.0000 50.0000 3.2592 0.3350 1.0000
60.2574 -34.0099 36.2677 60.4626 -34.1751 39.4387 1.2644
63.0109 -31.0961 -5.8663 62.8187 -29.7946 -4.0864 1.2630
61.2901 3.7196 -5.3901 61.4292 2.2480 -4.9620 1.8731
35.0831 -44.1164 3.7933 35.0232 -40.0716 1.5901 1.8645
22.7233 20.0904 -46.6940 23.0331 14.9730 -42.5619 2.0373
36.4612 47.8580 18.3852 36.2715 50.5065 21.2231 1.4146
90.8027 -2.0831 1.4410 91.1528 -1.6435 0.0447 1.4441
90.9257 -0.5406 -0.9208 88.6381 -0.8985 -0.7239 1.5381
6.7747 -0.2908 -2.4247 5.8714 -0.0985 -2.2286 0.6377
2.0776 0.0795 -1.1350 0.9033 -0.0636 -0.5514 0.9082
"""


@pytest.mark.parametrize("row", [r for r in SHARMA.strip().splitlines()])
def test_ciede2000_against_sharma_wu_and_dalal(row: str) -> None:
    v = [float(x) for x in row.split()]
    assert round(ciede2000((v[0], v[1], v[2]), (v[3], v[4], v[5])), 4) == v[6]


def test_machado_matrices_as_published() -> None:
    # Machado, Oliveira and Fernandes (2009), severity 1.0:
    # https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
    assert MACHADO["protanopia"][0] == (0.152286, 1.052583, -0.204868)
    assert MACHADO["deuteranopia"][2] == (-0.011820, 0.042940, 0.968881)
    assert MACHADO["tritanopia"][1] == (-0.078411, 0.930809, 0.147602)
    for m in MACHADO.values():  # each row sums to about 1: white stays white
        assert all(abs(sum(row) - 1) < 1e-5 for row in m)
    assert [round(x, 3) for x in simulate((1.0, 1.0, 1.0), "protanopia")] == [1.0, 1.0, 1.0]


def test_the_classic_pairs() -> None:
    tab10_red, tab10_green, tab10_orange, tab10_blue = (0.839, 0.153, 0.157), (0.173, 0.627, 0.173), (1.0, 0.498, 0.055), (0.122, 0.467, 0.706)
    kinds = {c.kind for c in clashes([tab10_red, tab10_green])}
    assert "deuteranopia" in kinds
    assert clashes([tab10_blue, tab10_orange]) == []  # the pair colour-blind-safe palettes are built on
