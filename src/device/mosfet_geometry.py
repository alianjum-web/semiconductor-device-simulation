"""2D planar MOSFET geometry: mesh, regions, contacts, interfaces (Sprint 2).

A structured (non-triangular) 2D mesh built directly with DEVSIM's own
mesh-line/region/contact primitives (create_2d_mesh / add_2d_mesh_line /
add_2d_region / add_2d_contact / add_2d_interface) -- the same box-meshing
approach DEVSIM's own bundled MOSFET test example uses
(.venv/devsim_data/testing/mos_2d_create.py). No Gmsh needed, per
docs/project_manual.md sec 2. Because this produces a structured
(quadrilateral) mesh rather than an unstructured triangular one, the
ordinary edge-based physics in devsim.python_packages.simple_physics
applies directly -- the element-based helpers in
devsim.python_packages.mos_physics are for triangular Gmsh meshes and are
not needed here.

Coordinate convention (all lengths in cm, matching the DEVSIM reference
example): y = 0 at the silicon surface (Si/oxide interface); y > 0 goes
down into the silicon body; y < 0 goes up through the oxide to the gate
contact. x = 0 at the left edge of the device; the channel is centered
between the source and drain regions.

The gate is an ideal metal contact placed directly on top of the oxide
(CreateOxideContact) rather than a separate doped polysilicon region --
gate work-function effects are therefore assumed away (flat-band voltage
~0), consistent with the "generic, physically-parameterized" device this
project models (docs/project_manual.md sec 6); this simplification is
recorded in docs/limitations.md.
"""

from dataclasses import dataclass

import devsim
from devsim.python_packages.model_create import CreateNodeModel

from src.device.mosfet_doping import mosfet_netdoping_expression

REGION_SILICON = "silicon"
REGION_OXIDE = "oxide"
INTERFACE_SI_OXIDE = "silicon_oxide"

CONTACT_GATE = "gate"
CONTACT_SOURCE = "source"
CONTACT_DRAIN = "drain"
CONTACT_BODY = "body"


@dataclass(frozen=True)
class MOSFETParams:
    # Sprint 3 sweep variables (docs/project_manual.md sec 4):
    channel_length_cm: float = 1.0e-4        # 1 um gate length
    oxide_thickness_cm: float = 1.0e-6       # 10 nm gate oxide
    channel_doping_cm3: float = 1.0e17       # N_A, p-type body/channel
    # Fixed for this project (not a primary sweep variable):
    source_drain_doping_cm3: float = 1.0e20  # N_D, n+ source/drain
    junction_depth_cm: float = 5.0e-6        # 50 nm source/drain diffusion depth
    extension_cm: float = 5.0e-5             # 0.5 um source/drain region width beyond the gate edge
    body_thickness_cm: float = 1.0e-4        # 1 um silicon depth from surface to body contact
    temperature_k: float = 300.0


def build_mosfet(mesh_name: str, device_name: str, params: MOSFETParams) -> dict:
    """Builds the 2D mesh, regions, contacts, interface, and doping for a
    planar NMOS. Returns the key x/y coordinates used (cm), for logging and
    reuse by the solver -- not meant to be re-derived elsewhere."""
    L = params.channel_length_cm
    t_ox = params.oxide_thickness_cm
    x_j = params.junction_depth_cm
    ext = params.extension_cm
    t_body = params.body_thickness_cm

    x_gate_left = ext
    x_gate_right = ext + L
    x_device_right = ext + L + ext

    y_gate_top = -t_ox           # gate contact sits here, top of the oxide
    y_oxide_mid = -0.5 * t_ox
    y_surface = 0.0               # Si/oxide interface
    y_junction = x_j
    y_body_mid = 0.5 * t_body
    y_body_bottom = t_body        # body contact sits here

    # DEVSIM's box-mesh contact detection is unreliable for a contact that
    # sits at the literal outer edge of the whole meshed domain (no mesh
    # line, hence no triangle, on the far side of it) -- confirmed by direct
    # experiment against this DEVSIM install, and the reason DEVSIM's own
    # bundled MOSFET test example (mos_2d_create.py) wraps its whole device
    # in a thin "air_thickness" margin on every contact-bearing side. Only
    # the gate and body contacts here are at the domain's outer y edges (the
    # source/drain contacts already have real air above them, since the
    # mesh extends up to y_gate_top well past y_surface), so only a top and
    # bottom margin are needed -- both claimed automatically by the
    # unbounded "air" region added below.
    air_margin_cm = 1.0e-7
    y_top_margin = y_gate_top - air_margin_cm
    y_bottom_margin = y_body_bottom + air_margin_cm

    devsim.create_2d_mesh(mesh=mesh_name)

    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_top_margin, ns=air_margin_cm, ps=air_margin_cm)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_gate_top, ns=t_ox / 50.0, ps=t_ox / 50.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_oxide_mid, ns=t_ox / 8.0, ps=t_ox / 8.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_surface, ns=t_ox / 50.0, ps=x_j / 20.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_junction, ns=x_j / 20.0, ps=x_j / 5.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_body_mid, ns=t_body / 10.0, ps=t_body / 10.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_body_bottom, ns=t_body / 50.0, ps=t_body / 50.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=y_bottom_margin, ns=air_margin_cm, ps=air_margin_cm)

    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=0.0, ns=ext / 10.0, ps=ext / 10.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=x_gate_left, ns=ext / 10.0, ps=L / 50.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=0.5 * (x_gate_left + x_gate_right), ns=L / 50.0, ps=L / 50.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=x_gate_right, ns=L / 50.0, ps=ext / 10.0)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=x_device_right, ns=ext / 10.0, ps=ext / 10.0)

    # DEVSIM's box mesher triangulates the full mesh-line grid; any cell not
    # claimed by an explicit region shows up as "Triangle has no region" and
    # leaves contact/interface matching on nearby regions unreliable. An
    # unbounded background region (same trick DEVSIM's own bundled MOSFET
    # test example uses for its "air" region) soaks up the leftover space
    # above the source/drain, beside the gate stack.
    devsim.add_2d_region(mesh=mesh_name, material="Air", region="air")
    devsim.add_2d_region(mesh=mesh_name, material="Silicon", region=REGION_SILICON,
                          xl=0.0, xh=x_device_right, yl=y_surface, yh=y_body_bottom)
    devsim.add_2d_region(mesh=mesh_name, material="Oxide", region=REGION_OXIDE,
                          xl=x_gate_left, xh=x_gate_right, yl=y_gate_top, yh=y_surface)

    devsim.add_2d_contact(mesh=mesh_name, name=CONTACT_GATE, region=REGION_OXIDE,
                           yl=y_gate_top, yh=y_gate_top, material="metal")
    devsim.add_2d_contact(mesh=mesh_name, name=CONTACT_SOURCE, region=REGION_SILICON,
                           yl=y_surface, yh=y_surface, xl=0.0, xh=x_gate_left,
                           material="metal")
    devsim.add_2d_contact(mesh=mesh_name, name=CONTACT_DRAIN, region=REGION_SILICON,
                           yl=y_surface, yh=y_surface, xl=x_gate_right, xh=x_device_right,
                           material="metal")
    devsim.add_2d_contact(mesh=mesh_name, name=CONTACT_BODY, region=REGION_SILICON,
                           yl=y_body_bottom, yh=y_body_bottom, material="metal")

    devsim.add_2d_interface(mesh=mesh_name, name=INTERFACE_SI_OXIDE,
                             region0=REGION_SILICON, region1=REGION_OXIDE)

    devsim.finalize_mesh(mesh=mesh_name)
    devsim.create_device(mesh=mesh_name, device=device_name)

    decay_cm = x_j / 5.0
    doping_expr = mosfet_netdoping_expression(
        x_gate_left=x_gate_left, x_gate_right=x_gate_right, y_junction=y_junction,
        na_cm3=params.channel_doping_cm3, nd_cm3=params.source_drain_doping_cm3,
        x_decay_cm=decay_cm, y_decay_cm=decay_cm,
    )
    CreateNodeModel(device_name, REGION_SILICON, "NetDoping", doping_expr)

    return {
        "x_gate_left": x_gate_left,
        "x_gate_right": x_gate_right,
        "x_device_right": x_device_right,
        "y_gate_top": y_gate_top,
        "y_surface": y_surface,
        "y_junction": y_junction,
        "y_body_bottom": y_body_bottom,
        "doping_decay_cm": decay_cm,
    }
