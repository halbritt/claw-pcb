#!/usr/bin/env python3
"""
Build a real Altium project using altium-monkey.

Creates:
  - A 2-layer PCB with board outline
  - Traces on top and bottom layers
  - SMT and through-hole pads
  - Silkscreen text + OpenClaw monkey face (circles + arcs)
  - SVG renderings of the board
  - Project stats

Output: output/ClawBoard.PcbDoc + SVGs
"""

from pathlib import Path
from altium_monkey import (
    AltiumBoardOutline,
    AltiumPcbDoc,
    BoardOutlineVertex,
    PadShape,
    PcbLayer,
    PcbSvgRenderOptions,
)
from altium_monkey.altium_pcb_surface import PCB_SurfaceSide

OUTPUT = Path(__file__).parent / "output"
OUTPUT.mkdir(exist_ok=True)

# ── Board dimensions (mils) ─────────────────────────────────────────────────
BOARD_W_MILS = 3200   # ~80mm
BOARD_H_MILS = 2400   # ~60mm

# ── Helpers ─────────────────────────────────────────────────────────────────

def make_outline(w: float, h: float) -> AltiumBoardOutline:
    return AltiumBoardOutline(vertices=[
        BoardOutlineVertex.line(0.0, 0.0),
        BoardOutlineVertex.line(w, 0.0),
        BoardOutlineVertex.line(w, h),
        BoardOutlineVertex.line(0.0, h),
    ])


def add_monkey_face(pcb: AltiumPcbDoc, cx: float, cy: float, r: float):
    """Draw the OpenClaw monkey face on silkscreen."""
    # Head circle
    pcb.add_arc(
        center_mils=(cx, cy),
        radius_mils=r,
        start_angle_degrees=0.0,
        end_angle_degrees=360.0,
        width_mils=12.0,
        layer=PcbLayer.TOP_OVERLAY,
    )
    # Left ear
    pcb.add_arc(
        center_mils=(cx - r * 0.7, cy - r * 0.8),
        radius_mils=r * 0.35,
        start_angle_degrees=0.0,
        end_angle_degrees=360.0,
        width_mils=10.0,
        layer=PcbLayer.TOP_OVERLAY,
    )
    # Right ear
    pcb.add_arc(
        center_mils=(cx + r * 0.7, cy - r * 0.8),
        radius_mils=r * 0.35,
        start_angle_degrees=0.0,
        end_angle_degrees=360.0,
        width_mils=10.0,
        layer=PcbLayer.TOP_OVERLAY,
    )
    # Left eye
    pcb.add_arc(
        center_mils=(cx - r * 0.35, cy - r * 0.1),
        radius_mils=r * 0.2,
        start_angle_degrees=0.0,
        end_angle_degrees=360.0,
        width_mils=8.0,
        layer=PcbLayer.TOP_OVERLAY,
    )
    # Right eye
    pcb.add_arc(
        center_mils=(cx + r * 0.35, cy - r * 0.1),
        radius_mils=r * 0.2,
        start_angle_degrees=0.0,
        end_angle_degrees=360.0,
        width_mils=8.0,
        layer=PcbLayer.TOP_OVERLAY,
    )
    # Nose
    pcb.add_arc(
        center_mils=(cx, cy + r * 0.25),
        radius_mils=r * 0.12,
        start_angle_degrees=0.0,
        end_angle_degrees=360.0,
        width_mils=8.0,
        layer=PcbLayer.TOP_OVERLAY,
    )
    # Mouth (arc from 200° to 340°)
    pcb.add_arc(
        center_mils=(cx, cy + r * 0.5),
        radius_mils=r * 0.5,
        start_angle_degrees=200.0,
        end_angle_degrees=340.0,
        width_mils=8.0,
        layer=PcbLayer.TOP_OVERLAY,
    )


def add_led_matrix(pcb: AltiumPcbDoc, start_x: float, start_y: float,
                   rows: int, cols: int, spacing_x: float, spacing_y: float,
                   net_prefix: str):
    """Add a grid of SMT pads representing an LED matrix."""
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * spacing_x
            y = start_y + r * spacing_y
            pcb.add_pad(
                designator=f"LED{r + 1}{c + 1}",
                position_mils=(x, y),
                width_mils=50.0,
                height_mils=50.0,
                shape=PadShape.RECTANGLE,
                layer=PcbLayer.TOP,
                net=f"{net_prefix}_R{r + 1}",
            )
            # Ground pad next to each LED
            pcb.add_pad(
                designator=f"LED{r + 1}{c + 1}_GND",
                position_mils=(x + 80.0, y),
                width_mils=50.0,
                height_mils=50.0,
                shape=PadShape.CIRCLE,
                layer=PcbLayer.TOP,
                net="GND",
            )


def add_component_footprint(pcb: AltiumPcbDoc, x: float, y: float,
                            designator: str, pins: list[tuple[float, float, str]]):
    """Add SMT pads for an IC."""
    for i, (dx, dy, net) in enumerate(pins):
        pcb.add_pad(
            designator=f"{designator}_{i + 1}",
            position_mils=(x + dx, y + dy),
            width_mils=40.0,
            height_mils=20.0,
            shape=PadShape.RECTANGLE,
            layer=PcbLayer.TOP,
            net=net,
        )


def add_trace_group(pcb: AltiumPcbDoc, segments: list[tuple[float, float, float, float]],
                    width_mils: float, layer: PcbLayer, net: str):
    """Add multiple trace segments."""
    for (x1, y1, x2, y2) in segments:
        pcb.add_track(
            (x1, y1), (x2, y2),
            width_mils=width_mils,
            layer=layer,
            net=net,
        )


# ── Build ────────────────────────────────────────────────────────────────────

def main():
    pcb = AltiumPcbDoc()

    # Board outline
    pcb.set_board_outline(make_outline(BOARD_W_MILS, BOARD_H_MILS))
    pcb.set_origin_to_outline_lower_left()

    # ── Nets ──
    for net in ["VCC", "GND", "USB_5V", "USB_D-", "USB_D+", "RESET",
                "PB1", "PB2", "PB3", "PB4", "PB5"]:
        pcb.add_net(net)

    # ── USB-C connector pads ──
    usb_x, usb_y = 400, BOARD_H_MILS / 2
    pcb.add_pad(
        designator="J1_1", position_mils=(usb_x - 60, usb_y - 80),
        width_mils=60, height_mils=40, shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM, net="GND",
    )
    pcb.add_pad(
        designator="J1_2", position_mils=(usb_x - 60, usb_y + 80),
        width_mils=60, height_mils=40, shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM, net="GND",
    )
    pcb.add_pad(
        designator="J1_3", position_mils=(usb_x + 60, usb_y - 80),
        width_mils=40, height_mils=30, shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM, net="USB_5V",
    )
    pcb.add_pad(
        designator="J1_4", position_mils=(usb_x + 60, usb_y + 80),
        width_mils=40, height_mils=30, shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM, net="USB_5V",
    )
    pcb.add_pad(
        designator="J1_5", position_mils=(usb_x, usb_y - 55),
        width_mils=30, height_mils=25, shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM, net="USB_D-",
    )
    pcb.add_pad(
        designator="J1_6", position_mils=(usb_x, usb_y + 55),
        width_mils=30, height_mils=25, shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM, net="USB_D+",
    )

    # ── ATtiny85 footprint (SOIC-8) ──
    mcu_x, mcu_y = BOARD_W_MILS / 2, BOARD_H_MILS / 2
    mcu_pins = [
        (-120, -90, "GND"), (-120, -30, "RESET"),
        (-120, 30, "PB5"), (-120, 90, "PB4"),
        (120, 90, "VCC"), (120, 30, "PB3"),
        (120, -30, "PB2"), (120, -90, "PB1"),
    ]
    add_component_footprint(pcb, mcu_x, mcu_y, "U1", mcu_pins)

    # ── LED matrix (5×5) ──
    add_led_matrix(pcb, 2000, 400, rows=5, cols=5,
                   spacing_x=120, spacing_y=100, net_prefix="LED")

    # ── Traces: USB to MCU ──
    add_trace_group(pcb, [
        (usb_x + 60, usb_y - 80, mcu_x + 120, mcu_y + 90),
    ], width_mils=20, layer=PcbLayer.TOP, net="VCC")

    add_trace_group(pcb, [
        (usb_x - 60, usb_y - 80, mcu_x - 120, mcu_y - 90),
    ], width_mils=20, layer=PcbLayer.BOTTOM, net="GND")

    # ── Traces: MCU to LED rows ──
    for i, row_net in enumerate(["PB1", "PB2", "PB3", "PB4", "PB5"]):
        src_x = mcu_x + 120 if i < 3 else mcu_x - 120
        src_y = mcu_y + 90 if i == 0 else (
            mcu_y - 90 if i == 1 else mcu_y + 30 if i == 2 else
            mcu_y - 30)
        dst_y = 400 + i * 100 + 25  # LED row center
        # L-shaped trace
        pcb.add_track((src_x, src_y), (src_x + 400, src_y),
                      width_mils=8, layer=PcbLayer.TOP, net=row_net)
        pcb.add_track((src_x + 400, src_y), (2000, dst_y),
                      width_mils=8, layer=PcbLayer.TOP, net=row_net)
        # Add vias to switch layers
        pcb.add_via(position_mils=(src_x + 400, src_y),
                    diameter_mils=60, hole_size_mils=30,
                    layer_start=1, layer_end=32, net=row_net)

    # ── Traces: LED columns to GND (zigzag pattern) ──
    for c in range(5):
        col_x = 2000 + c * 120 + 80 + 25  # ground pad x
        col_y = 400 + 4 * 100 + 25
        # Zigzag down to bottom
        y = col_y
        for step in range(6):
            x_offset = ((-1) ** step) * 30
            pcb.add_track((col_x + x_offset, y), (col_x + x_offset, y - 80),
                          width_mils=6, layer=PcbLayer.TOP, net="GND")
            y -= 80

    # ── Silkscreen text ──
    pcb.add_text(
        text="CLAW BOARD",
        position_mils=(800, BOARD_H_MILS - 200),
        height_mils=120,
        stroke_width_mils=14,
        layer=PcbLayer.TOP_OVERLAY,
    )
    pcb.add_text(
        text="built with altium-monkey 🦞",
        position_mils=(600, BOARD_H_MILS - 350),
        height_mils=60,
        stroke_width_mils=8,
        layer=PcbLayer.TOP_OVERLAY,
    )
    pcb.add_text(
        text="U1",
        position_mils=(mcu_x - 80, mcu_y - 160),
        height_mils=50,
        stroke_width_mils=6,
        layer=PcbLayer.TOP_OVERLAY,
    )
    pcb.add_text(
        text="J1",
        position_mils=(usb_x - 80, usb_y + 140),
        height_mils=50,
        stroke_width_mils=6,
        layer=PcbLayer.TOP_OVERLAY,
    )

    # ── Monkey face silkscreen ──
    add_monkey_face(pcb, cx=2800, cy=BOARD_H_MILS - 250, r=100)
    pcb.add_text(
        text="MADE WITH CODE",
        position_mils=(2650, BOARD_H_MILS - 420),
        height_mils=40,
        stroke_width_mils=5,
        layer=PcbLayer.TOP_OVERLAY,
    )

    # ── Filled regions (ground planes) ──
    pcb.add_fill(
        corner1_mils=(20, 20),
        corner2_mils=(BOARD_W_MILS - 20, BOARD_H_MILS - 20),
        layer=PcbLayer.TOP,
        net="GND",
    )

    # ── Save ──
    pcb_path = OUTPUT / "ClawBoard.PcbDoc"
    pcb.save(pcb_path)
    print(f"✅ Wrote {pcb_path}")

    # ── Generate SVGs ──
    # Top layer SVG
    opts_top = PcbSvgRenderOptions(
        visible_layers={PcbLayer.TOP},
        svg_display_scale=2.0,
        show_board_outline=True,
    )
    svg_top_data = pcb.to_svg(options=opts_top)
    svg_top_path = OUTPUT / "ClawBoard_top.svg"
    svg_top_path.write_text(svg_top_data)
    print(f"✅ Wrote {svg_top_path}")

    # Silkscreen SVG
    opts_silk = PcbSvgRenderOptions(
        visible_layers={PcbLayer.TOP_OVERLAY},
        svg_display_scale=2.0,
        show_board_outline=True,
    )
    svg_silk_data = pcb.to_svg(options=opts_silk)
    svg_silk_path = OUTPUT / "ClawBoard_silk.svg"
    svg_silk_path.write_text(svg_silk_data)
    print(f"✅ Wrote {svg_silk_path}")

    # Surface view SVG
    svg_surface_data = pcb.to_surface_svg(
        side=PCB_SurfaceSide.TOP,
        options=PcbSvgRenderOptions(svg_display_scale=2.0),
    )
    svg_surface_path = OUTPUT / "ClawBoard_surface.svg"
    svg_surface_path.write_text(svg_surface_data)
    print(f"✅ Wrote {svg_surface_path}")

    # ── Stats ──
    print("\n=== Board Stats ===")
    print(f"  Board: {BOARD_W_MILS}×{BOARD_H_MILS} mils ({BOARD_W_MILS/25.4:.0f}×{BOARD_H_MILS/25.4:.0f} mm)")
    nets = pcb.get_unique_footprints()
    print(f"  Nets defined: 11")
    print(f"  SVGs generated: 3 (top, silk, surface)")
    print(f"  Features: USB-C pads, SOIC-8 footprint, 5×5 LED grid, "
          f"monkey face silkscreen, ground plane, vias")


if __name__ == "__main__":
    main()
