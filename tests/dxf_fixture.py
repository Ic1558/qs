from __future__ import annotations

from pathlib import Path

import ezdxf


def write_minimal_dxf(path: Path) -> Path:
    doc = ezdxf.new("R2000")
    msp = doc.modelspace()
    msp.add_line((0, 0), (3000, 4000), dxfattribs={"layer": "ST-BEAM-CONC"})
    msp.add_lwpolyline(
        [(0, 0), (10000, 0), (10000, 10000), (0, 10000)],
        format="xy",
        close=True,
        dxfattribs={"layer": "ST - Floor Edges"},
    )
    msp.add_text("NOTE", dxfattribs={"layer": "ANNO-TEXT", "height": 250}).set_placement((0, 0))
    doc.saveas(path)
    return path
