// SPDX-FileCopyrightText: 2026 Curtis Galloway
// SPDX-License-Identifier: Apache-2.0
//
// Exploded assembly diagram for monitor_case.scad. Preview only.
//
//   openscad -D 'view="side"' --camera=0,0,0,90,0,90,0 --projection=o \
//     --viewall --autocenter --colorscheme=Nature --imgsize=1200,1200 \
//     -o docs/exploded_side.png exploded.scad
//   openscad -D 'view="iso"' --camera=0,0,0,60,0,225,0 --viewall \
//     --autocenter --colorscheme=Nature --imgsize=1200,1000 \
//     -o docs/exploded_iso.png exploded.scad
//
// Colors are chosen to stay distinct with red-green color blindness, and
// every part is also labeled in the side view.

include <monitor_case.scad>
part = "none";      // suppress monitor_case.scad's own output
view = "side";      // "side" (labeled) or "iso"
monitor_t = 25;

lift = 22;          // side view: tower raised off the clip
slide = 36;         // 3D view: tower slid out of the groove toward +x
off = view == "iso" ? [slide, 0, 0] : [0, 0, lift];
cover_out = 24;     // cover pulled forward of the pod
board_out = 12;     // board pulled forward of the pod
leg_out = [0, 10, -14];

c_clip = "RoyalBlue";
c_tower = "Gold";
c_leg = "DimGray";
c_board = "#303030";
c_cover = [1, 1, 1, 0.75];
c_metal = "Silver";

module arrow(from, to) {
  v = to - from;
  l = norm(v);
  color("black") translate(from)
    rotate([0, acos(v[2] / l), atan2(v[1], v[0])]) {
      cylinder(d = 0.6, h = l - 2.5, $fn = 12);
      translate([0, 0, l - 2.5]) cylinder(d1 = 2, d2 = 0, h = 2.5, $fn = 12);
    }
}

// Label in the y-z plane, readable from the -x side.
module label(t, y, z) {
  color("black") translate([-clip_w / 2 - 2, y, z]) rotate([90, 0, -90])
    mirror([1, 0, 0]) linear_extrude(0.4) text(t, size = 3.2, halign = "center");
}

module screw() {
  color(c_metal) rotate([0, 90, 0]) {
    cylinder(d = 3, h = 20, $fn = 16);
    translate([0, 0, -3]) cylinder(d = 5.5, h = 3, $fn = 24);
  }
}

module nut() {
  color(c_metal) rotate([0, 90, 0]) difference() {
    cylinder(d = 6.35, h = 2.4, $fn = 6);
    translate([0, 0, -1]) cylinder(d = 3, h = 5, $fn = 16);
  }
}

%translate([-60, 0, -60]) cube([120, monitor_t, 60]);

color(c_clip) clip();
color(c_tower) translate(off) tower();
color(c_board) translate(off + [-pcb_w / 2, pcb_front - board_out, in_z0])
  cube([pcb_w, pcb_t, pcb_h]);
color(c_cover) translate(off + [0, -cover_out, 0]) cover();
color(c_leg) translate(leg_out) leg_placed(monitor_t);
translate([-clip_w / 2 - 16, hinge_y, hinge_z]) screw();
translate([clip_w / 2 + 8, hinge_y, hinge_z]) nut();

// how each part moves into place
if (view == "iso")
  arrow([slide - 4, dt_yc, foot_z + foot_t + 4], [clip_w / 2 + 2, dt_yc, foot_z + foot_t + 4]);
arrow(off + [0, front - cover_out - 2, pod_top - 6], off + [0, front - 4, pod_top - 6]);
arrow([0, hinge_y + leg_out[1], hinge_z + leg_out[2]], [0, hinge_y + 1.5, hinge_z - 1.5]);
arrow([-clip_w / 2 - 6, hinge_y, hinge_z + 7], [-clip_w / 2 + 2, hinge_y, hinge_z + 7]);
arrow([clip_w / 2 + 6, hinge_y, hinge_z + 7], [clip_w / 2 - 2, hinge_y, hinge_z + 7]);

if (view == "side") {
  label("clip", 18, 5);
  label("tower", 18, pod_z0 + lift - 14);
  label("rail slides into the clip's", 26, foot_z + lift - 7);
  label("groove from the side", 26, foot_z + lift - 11);
  label("board", front - board_out, pod_top + lift + 4);
  label("cover", front - cover_out - 2, pod_top + lift + 10);
  label("leg", hinge_y + 12, -38);
  label("M3 screw + nut", hinge_y + 4, 10);
  label("monitor", monitor_t / 2, -50);
}
