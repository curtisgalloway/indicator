// SPDX-FileCopyrightText: 2026 Curtis Galloway
// SPDX-License-Identifier: Apache-2.0
//
// Monitor-top case for the bare Waveshare RP2040-Zero alert light.
//
// The clip hooks over the top edge of a monitor. At the clip's front edge a
// wall rises to a pod that holds the board upright, LED side facing the
// viewer and flush with the monitor's front, USB-C end down. Under the pod is
// an open gap: the plug drops through the pod floor into it, and the cable
// bends back, runs over the monitor's top and down the back. The rear leg is
// hinged on an M3 screw so one clip fits monitors from monitor_min to
// monitor_max thick; tightening the nut sets how stiffly it swings.
//
// Four parts:
//   clip  - top plate, front lip, hinge knuckles, opaque. Print face down.
//   tower - front wall + pod, slides into the clip's dovetail. Print on its side.
//   leg   - hinged rear leg, opaque filament. Print on its side.
//   cover - front window, translucent filament. Print face down.
//
// Render one part:  openscad -D 'part="clip"' -o clip.stl monitor_case.scad
//
// Axes: x = across the monitor, y = front to back (viewer at -y),
// z = up. The monitor's top surface is z = 0, its front face y = 0.

part = "assembly";  // "clip", "tower", "leg", "cover", "fit_test", or "assembly"

/* [Monitor] */
monitor_min = 15;   // thinnest monitor the hinged leg reaches
monitor_max = 35;   // thickest monitor the clip fits over
monitor_t = 20;     // preview only: the ghost monitor's thickness
monitor_fit = 0.4;  // extra room so the clip slides on
front_lip = 8;      // how far the clip drops over the front bezel

/* [Hinged rear leg, M3 x 20 screw + M3 nut] */
leg_len = 34;       // hinge axis to tip center
knuckle_d = 9;      // hinge barrel diameter
tip_d = 3;          // rounded tip that touches the monitor's back
outer_k = 6;        // width of each of the clip's two outer knuckles
k_gap = 0.25;       // side gap between knuckles
screw_d = 3.4;      // M3 clearance hole
head_d = 6.0;       // M3 socket head counterbore
head_depth = 3.0;
nut_d = 6.6;        // M3 nut pocket, across corners
nut_depth = 2.6;

/* [Board: Waveshare RP2040-Zero] */
pcb_w = 18;         // across (x)
pcb_h = 23.5;       // along the USB axis (z, USB end down)
pcb_t = 1.0;        // PCB thickness
pcb_clr = 0.3;      // pocket clearance around the PCB
usb_h = 3.3;        // USB-C receptacle height above the PCB's top face
usb_len = 7.5;      // receptacle length up the board from its bottom edge

/* [USB-C plug and cable] */
plug_w = 13;        // molded plug body width; measure your cable
plug_d = 7.5;       // molded plug body thickness
plug_len = 22;      // plug body length below the receptacle, strain relief
                    // included. A right-angle plug needs much less.
cable_bend = 10;    // room under the plug for the cable to turn back

/* [Shell] */
wall = 2.4;
plate_t = 4.4;      // clip top plate; thick enough for the dovetail groove
floor_t = 2.0;      // pod floor
riser_t = 3.0;      // front wall holding the pod up
foot_len = 14;      // tower's foot, which carries the dovetail rail
foot_t = 2.0;

/* [Tower-to-clip joint: sliding dovetail] */
// The clip has a dovetail groove across its top plate, closed at the -x end.
// A tower's foot carries the matching rail and slides in from +x; friction
// holds it. Any tower built on dovetail_rail() fits the same clip.
dt_y = 7;           // groove center, behind the clip's front face
dt_top = 6;         // groove width at the plate's top face
dt_depth = 2.2;     // groove depth; the 45-degree walls widen it by this much
dt_stop = 1.6;      // closed end of the groove, at the -x side
dt_chamfer = 0.4;   // flare at the groove mouth for first-layer squish
joint_fit = 0.15;   // rail clearance per side; tune it with part="fit_test"
fit_tests = [0.10, 0.15, 0.20];  // rail clearances printed by part="fit_test"
cover_t = 1.2;      // translucent window thickness (thinner = brighter)
rim_t = 0.8;        // cover's friction rim
rim_d = 1.5;        // how far the rim enters the pod
rim_fit = 0.15;     // rim clearance; lower for a tighter press fit
clip_w = pcb_w + 2 * (pcb_clr + wall);  // clip width = pod width

$fn = 32;
eps = 0.01;

// ---- Derived layout ---------------------------------------------------

front = -wall;                               // outer face of the front lip

// Hinge axis: behind the thickest monitor by one barrel radius, so the leg's
// front edge clears it when the leg hangs nearly straight down.
hinge_r = knuckle_d / 2;
hinge_y = monitor_max + monitor_fit + hinge_r;
hinge_z = plate_t - hinge_r;                 // barrel top flush with the plate
foot_z = plate_t;                            // tower bottom, on the plate
dt_yc = front + dt_y;                        // groove center, y
center_k = clip_w - 2 * (outer_k + k_gap);   // the leg's knuckle width

// Leg angle (forward from straight down) where the tip meets a monitor of
// thickness t. Thin monitors need the steepest angle.
function leg_angle(t) = asin((hinge_y - tip_d / 2 - t) / leg_len);
assert(leg_angle(monitor_min) <= 50, "leg_len too short for monitor_min");

// Window face flush with the front lip.
pod_front = front + cover_t;
// The plug body hangs into the gap, so it must clear the riser behind the
// window by 0.5 mm.
plug_y = front + riser_t + 0.5 + plug_d / 2; // plug center, y
pcb_front = plug_y + usb_h / 2;              // PCB front (LED) face, y
pcb_back = pcb_front + pcb_t;
cover_gap = pcb_front - pod_front;           // window inner face to PCB face
pod_back = pcb_back + pcb_clr + wall;

gap_z0 = foot_z + foot_t;                    // top of the tower's foot
pod_z0 = gap_z0 + plug_len + cable_bend - floor_t;   // pod floor bottom
in_z0 = pod_z0 + floor_t;                    // PCB rests here
in_z1 = in_z0 + pcb_h + pcb_clr;             // pod interior top
pod_top = in_z1 + wall;
in_w = pcb_w + 2 * pcb_clr;                  // pod interior width

assert(pod_back <= monitor_min, "monitor_min too small for the pod depth");
echo(str("leg angle: ", leg_angle(monitor_min), " deg at ", monitor_min,
         " mm, ", leg_angle(monitor_max), " deg at ", monitor_max, " mm"));
echo(str("cover_gap (window to PCB face) = ", cover_gap, " mm"));
echo(str("cable gap under the pod = ", pod_z0 - gap_z0, " mm"));
echo(str("case top is ", pod_top, " mm above the monitor top"));

// ---- Base -------------------------------------------------------------

// A shape extruded along x, centered, from a 2D profile drawn in (y, z).
module along_x(w) {
  rotate([90, 0, 90]) linear_extrude(w, center = true) children();
}

module clip() {
  difference() {
    union() {
      // top plate and front lip
      translate([-clip_w / 2, front, 0]) cube([clip_w, hinge_y - front, plate_t]);
      translate([-clip_w / 2, front, -front_lip]) cube([clip_w, wall, front_lip + plate_t]);
      // two outer hinge knuckles, squared off at the rear top so they sit
      // flat on the bed when the clip prints face down
      for (s = [-1, 1])
        translate([s * (clip_w - outer_k) / 2, 0, 0])
          along_x(outer_k) hull() {
            translate([hinge_y, hinge_z]) circle(d = knuckle_d);
            translate([hinge_y, hinge_z]) square([hinge_r, hinge_r]);
          }
    }
    // room for the leg's knuckle to turn
    along_x(center_k + 2 * k_gap) translate([hinge_y, hinge_z])
      circle(r = hinge_r + 0.5);
    translate([-center_k / 2 - k_gap, hinge_y - hinge_r - 2.5, hinge_z - hinge_r - 1])
      cube([center_k + 2 * k_gap, knuckle_d + 3, knuckle_d + 2]);
    // dovetail groove for the tower's rail, closed at the -x end
    translate([dt_stop / 2 + 0.5, 0, 0])
      along_x(clip_w - dt_stop + 1) dovetail_groove_profile();
    // M3 screw hole, head counterbore on -x, nut pocket on +x
    translate([0, hinge_y, hinge_z]) {
      rotate([0, 90, 0]) cylinder(d = screw_d, h = clip_w + 2, center = true);
      translate([-clip_w / 2 - eps, 0, 0]) rotate([0, 90, 0])
        cylinder(d = head_d, h = head_depth + eps);
      translate([clip_w / 2 - nut_depth, 0, 0]) rotate([0, 90, 0])
        cylinder(d = nut_d, h = nut_depth + eps, $fn = 6);
    }
  }
}

// ---- Dovetail joint --------------------------------------------------

// Groove core cross-section in (y, z): straight-sided down to the neck
// dt_chamfer below the top face, then widening at 45 degrees to the floor.
module dovetail_core_profile() {
  a = dt_top / 2;
  w = a + dt_depth - dt_chamfer;             // half-width at the floor
  polygon([
    [dt_yc - a, plate_t + 1], [dt_yc + a, plate_t + 1],
    [dt_yc + a, plate_t - dt_chamfer],
    [dt_yc + w, plate_t - dt_depth], [dt_yc - w, plate_t - dt_depth],
    [dt_yc - a, plate_t - dt_chamfer],
  ]);
}

// Groove cut into the clip: the core plus a 45-degree flare at the mouth.
// With the clip printed face down the mouth is on the bed, so the flare
// absorbs first-layer squish; above the neck the walls widen at 45 degrees,
// which prints without support, and the floor bridges about 10 mm.
module dovetail_groove_profile() {
  a = dt_top / 2;
  c = dt_chamfer;
  dovetail_core_profile();
  polygon([
    [dt_yc - a - c, plate_t + 1], [dt_yc + a + c, plate_t + 1],
    [dt_yc + a + c, plate_t], [dt_yc + a, plate_t - c],
    [dt_yc - a, plate_t - c], [dt_yc - a - c, plate_t],
  ]);
}

// Rail cross-section: the groove core shrunk by the fit on every face,
// trimmed 0.2 mm short of the floor so it bears on the slanted walls.
module dovetail_rail_profile(fit) {
  intersection() {
    offset(delta = -fit) dovetail_core_profile();
    translate([dt_yc - 20, plate_t - dt_depth + 0.2])
      square([40, dt_depth - 0.2 + eps]);
  }
}

// The rail under a tower's foot, stopping short of the groove's closed end.
module dovetail_rail(fit = joint_fit) {
  l = clip_w - dt_stop - 0.3;
  translate([clip_w / 2 - l / 2, 0, 0]) along_x(l) dovetail_rail_profile(fit);
}

// Fit test: a 10 mm slice of the clip's groove (open at both ends) and one
// short rail per clearance in fit_tests, marked with 1, 2, 3... notches.
// Pick the rail that slides in with firm hand pressure and set joint_fit.
module fit_test() {
  // groove slice, face down like the clip
  translate([0, 0, plate_t]) rotate([180, 0, 0]) difference() {
    translate([-5, front, 0]) cube([10, foot_len, plate_t]);
    along_x(12) dovetail_groove_profile();
  }
  // rails standing on end, like the tower on its side, 10 mm apart
  for (i = [0 : len(fit_tests) - 1])
    translate([16 + i * 10, 0, 0]) rotate([0, -90, 0]) difference() {
      union() {
        translate([0, dt_yc - dt_top / 2 - 2, foot_z]) cube([10, dt_top + 4, foot_t]);
        translate([5, 0, 0]) along_x(10) dovetail_rail_profile(fit_tests[i]);
      }
      // i + 1 notches at the top, to tell the rails apart
      for (n = [0 : i])
        translate([10 - 1.2 - n * 2, dt_yc + dt_top / 2 + 1, foot_z - 1])
          cube([0.8, 2, foot_t + 2]);
    }
}

// ---- Leg --------------------------------------------------------------

// Leg profile in (y, z), hanging straight down from the hinge axis at the
// origin: a barrel tapering to the rounded tip.
module leg_profile() {
  hull() {
    circle(d = knuckle_d);
    translate([0, -leg_len]) circle(d = tip_d);
  }
}

// The leg, hinge axis on the x axis. One width throughout, the width of the
// knuckle that fits between the clip's outer knuckles, so it prints on its
// side with no overhangs.
module leg() {
  difference() {
    along_x(center_k) leg_profile();
    rotate([0, 90, 0]) cylinder(d = screw_d, h = clip_w + 2, center = true);
  }
}

// The leg in place on the clip, swung forward to touch a monitor of
// thickness t.
module leg_placed(t) {
  translate([0, hinge_y, hinge_z]) rotate([-leg_angle(t), 0, 0]) leg();
}

// ---- Tower ------------------------------------------------------------

module riser() {
  // foot with the dovetail rail, then the front wall up to the pod floor;
  // the gap behind the wall is open at both sides and the back
  translate([-clip_w / 2, front, foot_z]) cube([clip_w, foot_len, foot_t]);
  dovetail_rail();
  translate([-clip_w / 2, front, foot_z]) cube([clip_w, riser_t, pod_z0 - foot_z + eps]);
}

module pod() {
  difference() {
    translate([-clip_w / 2, pod_front, pod_z0])
      cube([clip_w, pod_back - pod_front, pod_top - pod_z0]);
    // board pocket, open at the front
    translate([-in_w / 2, pod_front - eps, in_z0])
      cube([in_w, pcb_back + pcb_clr - pod_front + eps, in_z1 - in_z0]);
    // USB-C plug drops through the floor into the gap
    translate([-plug_w / 2, plug_y - plug_d / 2, pod_z0 - eps])
      cube([plug_w, plug_d, floor_t + 2 * eps]);
  }
}

module tower() {
  riser();
  pod();
}

// ---- Cover ------------------------------------------------------------

module cover() {
  rw = in_w - 2 * rim_fit;                   // rim outer width
  rz0 = in_z0 + usb_len + 1;                 // rim sides stop above the USB-C
  rz1 = in_z1 - rim_fit;
  // window, flush with the riser and front lip
  translate([-clip_w / 2, front, pod_z0]) cube([clip_w, cover_t, pod_top - pod_z0]);
  // friction rim: top edge and the upper part of both sides. No bottom edge,
  // where the USB-C receptacle sits.
  translate([-rw / 2, pod_front - eps, rz1 - rim_t]) cube([rw, rim_d, rim_t]);
  for (s = [-1, 1])
    translate([s > 0 ? rw / 2 - rim_t : -rw / 2, pod_front - eps, rz0])
      cube([rim_t, rim_d, rz1 - rz0]);
  // posts that press the PCB's top corners against the pod's back wall
  for (s = [-1, 1])
    translate([s * (rw / 2 - 1) - 1, pod_front - eps, rz1 - 2.5])
      cube([2, cover_gap + eps, 2.5]);
  // pad that presses on the USB-C receptacle, holding the bottom end
  translate([-3, pod_front - eps, in_z0 + 1.5])
    cube([6, cover_gap - usb_h - 0.2 + eps, usb_len - 2.5]);
}

// ---- Output -----------------------------------------------------------

module monitor_ghost() {
  %translate([-60, 0, -60]) cube([120, monitor_t, 60]);
}

module pcb_ghost() {
  %translate([-pcb_w / 2, pcb_front, in_z0]) cube([pcb_w, pcb_t, pcb_h]);
  %translate([-4.5, pcb_front - usb_h, in_z0]) cube([9, usb_h, usb_len]);
  // plug body
  %translate([-plug_w / 2, plug_y - plug_d / 2, in_z0 - plug_len])
    cube([plug_w, plug_d, plug_len]);
}

if (part == "clip") {
  // face down: top plate on the bed, lip and hinge knuckles pointing up
  translate([0, 0, plate_t]) rotate([180, 0, 0]) clip();
} else if (part == "tower") {
  // on its side, no supports
  translate([0, 0, clip_w / 2]) rotate([0, 90, 0]) tower();
} else if (part == "leg") {
  // on its side, no supports
  translate([0, 0, center_k / 2]) rotate([0, 90, 0]) leg();
} else if (part == "fit_test") {
  fit_test();
} else if (part == "cover") {
  // window face down
  rotate([90, 0, 0]) translate([0, -front, 0]) cover();
} else if (part == "assembly") {
  monitor_ghost();
  pcb_ghost();
  color("dimgray") clip();
  color("gray") tower();
  color("slategray") leg_placed(monitor_t);
  color("white", 0.6) cover();
}
