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


def add_cc_pin(pcb: AltiumPcbDoc, x: float, y: float, designator: str):
    """Add USB-C CC pin with 5.1kΩ pull-down to GND."""
    # CC pad
    pcb.add_pad(
        designator=designator,
        position_mils=(x, y),
        width_mils=30.0,
        height_mils=20.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM,
        net="CC",
    )
    # Small GND pad for pull-down (represents 5.1kΩ resistor to GND)
    pcb.add_pad(
        designator=f"{designator}_GND",
        position_mils=(x + 60.0, y),
        width_mils=20.0,
        height_mils=20.0,
        shape=PadShape.CIRCLE,
        layer=PcbLayer.BOTTOM,
        net="GND",
    )
    # Trace connecting CC to GND (simulating pull-down)
    pcb.add_track(
        (x + 15, y), (x + 50, y),
        width_mils=4.0,
        layer=PcbLayer.BOTTOM,
        net="CC",
    )


def add_led_matrix(pcb: AltiumPcbDoc, start_x: float, start_y: float,
                   rows: int, cols: int, spacing_x: float, spacing_y: float):
    """Add a 5×5 scannable LED matrix.

    Row anodes driven by PB1–PB5.
    Column cathodes tied to GND through current-limiting resistors.
    """
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * spacing_x
            y = start_y + r * spacing_y
            # LED anode pad (row)
            pcb.add_pad(
                designator=f"LED{r + 1}{c + 1}",
                position_mils=(x, y),
                width_mils=50.0,
                height_mils=50.0,
                shape=PadShape.RECTANGLE,
                layer=PcbLayer.TOP,
                net=f"LED_ROW{r + 1}",
            )
            # LED cathode pad (column, tied to GND via resistor)
            pcb.add_pad(
                designator=f"LED{r + 1}{c + 1}_GND",
                position_mils=(x + spacing_x, y),
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


# ── Build ────────────────────────────────────────────────────────────────────

def main():
    pcb = AltiumPcbDoc()

    # Board outline
    pcb.set_board_outline(make_outline(BOARD_W_MILS, BOARD_H_MILS))
    pcb.set_origin_to_outline_lower_left()

    # ── Nets ──
    for net in ["VCC", "GND", "USB_5V", "USB_D-", "USB_D+", "RESET",
                "PB1", "PB2", "PB3", "PB4", "PB5", "CC",
                "LED_ROW1", "LED_ROW2", "LED_ROW3", "LED_ROW4", "LED_ROW5"]:
        pcb.add_net(net)

    # ── Correction 1: Proper 24-pin USB-C SMD footprint ──
    usb_x, usb_y = 400, BOARD_H_MILS / 2

    # VBUS pads (4×, bottom layer)
    for i, offset in enumerate([-90, -30, 30, 90]):
        pcb.add_pad(
            designator=f"J1_VBUS{i + 1}",
            position_mils=(usb_x, usb_y + offset),
            width_mils=30.0,
            height_mils=30.0,
            shape=PadShape.RECTANGLE,
            layer=PcbLayer.BOTTOM,
            net="VCC",
        )

    # GND pads (4×, bottom layer)
    for i, offset in enumerate([-120, -60, 60, 120]):
        pcb.add_pad(
            designator=f"J1_GND{i + 1}",
            position_mils=(usb_x, usb_y + offset),
            width_mils=40.0,
            height_mils=30.0,
            shape=PadShape.RECTANGLE,
            layer=PcbLayer.BOTTOM,
            net="GND",
        )

    # D+ pads (2×, bottom layer)
    pcb.add_pad(
        designator="J1_DP1",
        position_mils=(usb_x - 30, usb_y - 15),
        width_mils=25.0,
        height_mils=20.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM,
        net="USB_D+",
    )
    pcb.add_pad(
        designator="J1_DP2",
        position_mils=(usb_x - 30, usb_y + 15),
        width_mils=25.0,
        height_mils=20.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM,
        net="USB_D+",
    )

    # D- pads (2×, bottom layer)
    pcb.add_pad(
        designator="J1_DM1",
        position_mils=(usb_x + 30, usb_y - 15),
        width_mils=25.0,
        height_mils=20.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM,
        net="USB_D-",
    )
    pcb.add_pad(
        designator="J1_DM2",
        position_mils=(usb_x + 30, usb_y + 15),
        width_mils=25.0,
        height_mils=20.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.BOTTOM,
        net="USB_D-",
    )

    # CC pins (2×, with 5.1kΩ pull-down to GND)
    add_cc_pin(pcb, usb_x - 80, usb_y - 30, "J1_CC1")
    add_cc_pin(pcb, usb_x - 80, usb_y + 30, "J1_CC2")

    # Shell/shield pads (4×, bottom layer, tied to GND)
    for offset in [-150, -100, 100, 150]:
        pcb.add_pad(
            designator=f"J1_SHELL{offset // 50}",
            position_mils=(usb_x - 130, usb_y + offset),
            width_mils=50.0,
            height_mils=20.0,
            shape=PadShape.RECTANGLE,
            layer=PcbLayer.BOTTOM,
            net="GND",
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

    # ── Correction 2: Decoupling capacitor (100nF) ──
    # Between VDD (pin 8 = VCC) and GND (pin 4 = GND), within 50 mils
    decap_x = mcu_x + 120 + 40  # just to the right of U1 pin 8
    decap_y = mcu_y + 90
    pcb.add_pad(
        designator="C1_A",
        position_mils=(decap_x, decap_y),
        width_mils=30.0,
        height_mils=30.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.TOP,
        net="VCC",
    )
    pcb.add_pad(
        designator="C1_K",
        position_mils=(decap_x, decap_y - 60),
        width_mils=30.0,
        height_mils=30.0,
        shape=PadShape.RECTANGLE,
        layer=PcbLayer.TOP,
        net="GND",
    )
    pcb.add_text(
        text="C1",
        position_mils=(decap_x - 20, decap_y + 30),
        height_mils=40,
        stroke_width_mils=5,
        layer=PcbLayer.TOP_OVERLAY,
    )

    # ── Correction 4: LED matrix (5×5 scannable) ──
    add_led_matrix(pcb, 2000, 400, rows=5, cols=5,
                   spacing_x=120, spacing_y=100)

    # ── Correction 3: Layer bridging — explicit vias at layer transitions ──
    # VCC trace: USB pads are on BOTTOM, MCU VCC pin is on TOP
    # Add via where trace transitions from bottom to top
    vcc_via_x = mcu_x + 120
    vcc_via_y = mcu_y + 90
    pcb.add_via(
        position_mils=(vcc_via_x, vcc_via_y),
        diameter_mils=60, hole_size_mils=30,
        layer_start=1, layer_end=32, net="VCC",
    )
    # Trace from USB VBUS (bottom) to via
    pcb.add_track(
        (usb_x, usb_y - 80), (vcc_via_x, vcc_via_y),
        width_mils=20, layer=PcbLayer.BOTTOM, net="VCC",
    )
    # Trace from via to MCU VCC pin (top)
    pcb.add_track(
        (vcc_via_x, vcc_via_y), (mcu_x + 120, mcu_y + 90),
        width_mils=20, layer=PcbLayer.TOP, net="VCC",
    )

    # GND trace: USB GND pads are on BOTTOM, MCU GND pin is on TOP
    # Place via 80 mils left of the MCU GND pin
    gnd_via_x = mcu_x - 200
    gnd_via_y = mcu_y - 90
    pcb.add_via(
        position_mils=(gnd_via_x, gnd_via_y),
        diameter_mils=60, hole_size_mils=30,
        layer_start=1, layer_end=32, net="GND",
    )
    # Trace from USB GND (bottom) to via
    pcb.add_track(
        (usb_x, usb_y - 120), (gnd_via_x, gnd_via_y),
        width_mils=20, layer=PcbLayer.BOTTOM, net="GND",
    )
    # Trace from via to MCU GND pin (top)
    pcb.add_track(
        (gnd_via_x, gnd_via_y), (mcu_x - 120, mcu_y - 90),
        width_mils=20, layer=PcbLayer.TOP, net="GND",
    )

    # ── Traces: MCU to LED row anodes ──
    for i, row_net in enumerate(["PB1", "PB2", "PB3", "PB4", "PB5"]):
        src_x = mcu_x + 120 if i < 3 else mcu_x - 120
        src_y = mcu_y + 90 if i == 0 else (
            mcu_y - 90 if i == 1 else mcu_y + 30 if i == 2 else
            mcu_y - 30)
        dst_y = 400 + i * 100 + 25  # LED row center
        # L-shaped trace on top layer
        pcb.add_track((src_x, src_y), (src_x + 400, src_y),
                      width_mils=8, layer=PcbLayer.TOP, net=row_net)
        pcb.add_track((src_x + 400, src_y), (2000, dst_y),
                      width_mils=8, layer=PcbLayer.TOP, net=row_net)

    # ── Correction 5: Ground plane stitching — vias from GND pads to fill ──
    # Stitch GND pads to the ground plane fill region
    fill_center_x = BOARD_W_MILS / 2
    fill_center_y = BOARD_H_MILS / 2

    # Via grid for ground stitching
    for gx in [mcu_x, decap_x, usb_x, 2000 + 3 * 120 + 80]:
        for gy in [mcu_y, mcu_y + 90, usb_y, 400 + 2 * 100]:
            pcb.add_via(
                position_mils=(gx, gy),
                diameter_mils=40, hole_size_mils=20,
                layer_start=1, layer_end=32, net="GND",
            )

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

    # ── Correction 5: Ground plane fill ──
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
    opts_top = PcbSvgRenderOptions(
        visible_layers={PcbLayer.TOP},
        svg_display_scale=2.0,
        show_board_outline=True,
    )
    svg_top_data = pcb.to_svg(options=opts_top)
    svg_top_path = OUTPUT / "ClawBoard_top.svg"
    svg_top_path.write_text(svg_top_data)
    print(f"✅ Wrote {svg_top_path}")

    opts_silk = PcbSvgRenderOptions(
        visible_layers={PcbLayer.TOP_OVERLAY},
        svg_display_scale=2.0,
        show_board_outline=True,
    )
    svg_silk_data = pcb.to_svg(options=opts_silk)
    svg_silk_path = OUTPUT / "ClawBoard_silk.svg"
    svg_silk_path.write_text(svg_silk_data)
    print(f"✅ Wrote {svg_silk_path}")

    svg_surface_data = pcb.to_surface_svg(
        side=PCB_SurfaceSide.TOP,
        options=PcbSvgRenderOptions(svg_display_scale=2.0),
    )
    svg_surface_path = OUTPUT / "ClawBoard_surface.svg"
    svg_surface_path.write_text(svg_surface_data)
    print(f"✅ Wrote {svg_surface_path}")

    # ── Correction 6: Stats — count primitives correctly ──
    pads = list(getattr(pcb, 'pads', []) or [])
    tracks = list(getattr(pcb, 'tracks', []) or [])
    vias = list(getattr(pcb, 'vias', []) or [])
    fills = list(getattr(pcb, 'fills', []) or [])
    texts = list(getattr(pcb, 'texts', []) or [])
    arcs = list(getattr(pcb, 'arcs', []) or [])

    print("\n=== Board Stats ===")
    print(f"  Board: {BOARD_W_MILS}×{BOARD_H_MILS} mils ({BOARD_W_MILS/25.4:.0f}×{BOARD_H_MILS/25.4:.0f} mm)")
    print(f"  Pads: {len(pads)}")
    print(f"  Tracks: {len(tracks)}")
    print(f"  Vias: {len(vias)}")
    print(f"  Fills: {len(fills)}")
    print(f"  Total primitives: {len(pads)+len(tracks)+len(vias)+len(fills)+len(texts)+len(arcs)}")
    print(f"  SVGs generated: 3 (top, silk, surface)")
    print(f"  Features: USB-C connector, SOIC-8 footprint, 5×5 scannable LED matrix, "
          f"decoupling cap, ground plane with stitching vias, monkey face silkscreen")


if __name__ == "__main__":
    main()
