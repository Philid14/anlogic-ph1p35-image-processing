/* FRAME_CONCEPT_V1 — entry point; OpenSCAD 2021.01+; no external library.
   Concept assembly only. Use PARAMETERS.md before changing hardware dimensions. */
include <parameters.scad>
include <common.scad>
include <camera_mount.scad>
include <monitor_mount.scad>
include <board_tray.scad>
include <light_mount.scad>
include <fixtures.scad>

module base_and_frame() {
    color([0.66,0.57,0.43]) translate([base_left,-base_d/2,-base_t]) cube([base_w,base_d,base_t]);
    color([0.15,0.17,0.19]) for(x=[base_left+35,frame_w/2-35,base_right-35],y=[-base_d/2+35,base_d/2-35])
        translate([x,y,-base_t-foot_h]) cylinder(d=35,h=foot_h);
    color([0.63,0.67,0.71]) {
        for(x=[-frame_w/2,frame_w/2-profile],y=[-frame_d/2,frame_d/2-profile])
            translate([x,y,0]) cube([profile,profile,frame_h]);
        for(z=[0,frame_h-profile]) {
            for(y=[-frame_d/2,frame_d/2-profile]) translate([-frame_w/2+profile,y,z]) cube([frame_w-2*profile,profile,profile]);
            for(x=[-frame_w/2,frame_w/2-profile]) translate([x,-frame_d/2+profile,z]) cube([profile,frame_d-2*profile,profile]);
        }
        // Rear X brace; side diagonals; front opening stays accessible.
        for(s=[-1,1]) beam_between([s*(frame_w/2-profile),frame_d/2-profile/2,profile],
            [-s*(frame_w/2-profile),frame_d/2-profile/2,frame_h-profile],8);
        for(s=[-1,1]) beam_between([s*(frame_w/2-profile/2),-frame_d/2+profile,profile],
            [s*(frame_w/2-profile/2),frame_d/2-profile,frame_h-profile],8);
        // Small base anchors are symbolic; fastener sizing follows load review.
        for(x=[-frame_w/2,frame_w/2-45],y=[-frame_d/2,frame_d/2-45])
            translate([x,y,0]) cube([45,45,4]);
    }
    // Cable lane stays at outer right edge, clear of the lens field.
    color([0.18,0.2,0.23]) translate([frame_w/2+cloth_gap+3,-frame_d/2,20])
        cube([cable_lane_w,20,frame_h-60]);
}

module curtain_hooks() {
    color([0.17,0.19,0.21]) {
        for(x=[-frame_w/2:cloth_hook_pitch:frame_w/2],s=[-1,1])
            translate([x,s*(frame_d/2+cloth_gap),frame_h]) difference() {
                cylinder(d=10,h=5); translate([0,0,-eps]) cylinder(d=5,h=5+2*eps);
            }
        for(y=[-frame_d/2:cloth_hook_pitch:frame_d/2],s=[-1,1])
            translate([s*(frame_w/2+cloth_gap),y,frame_h]) difference() {
                cylinder(d=10,h=5); translate([0,0,-eps]) cylinder(d=5,h=5+2*eps);
            }
    }
}

module curtains() {
    // Semi-transparent for inspection only; actual material must be opaque/matte.
    color([0.04,0.05,0.07,0.23]) {
        translate([-frame_w/2-cloth_gap,-frame_d/2-cloth_gap,frame_h+5]) cube([frame_w+2*cloth_gap,frame_d+2*cloth_gap,1]);
        translate([-frame_w/2-cloth_gap,frame_d/2+cloth_gap,0]) cube([frame_w+2*cloth_gap,1,frame_h]);
        translate([-frame_w/2-cloth_gap,-frame_d/2-cloth_gap,0]) cube([1,frame_d+2*cloth_gap,frame_h]);
        // Right service slit: 45 x 25 assumed aperture; cover with two offset flaps.
        difference() {
            translate([frame_w/2+cloth_gap,-frame_d/2-cloth_gap,0]) cube([1,frame_d+2*cloth_gap,frame_h]);
            translate([frame_w/2+cloth_gap-eps,board_y-cable_pass_w/2,lens_z-cable_pass_h/2])
                cube([1+2*eps,cable_pass_w,cable_pass_h]);
        }
        if(!front_open) translate([-frame_w/2-cloth_gap,-frame_d/2-cloth_gap,0]) cube([frame_w+2*cloth_gap,1,frame_h]);
    }
}

module cable_routes() {
    // Endpoints are symbolic: connector orientation/pinout and allowable lengths unknown.
    cable_path([[camera_xy[0]+20,camera_xy[1]+20,camera_plate_z-5],
        [80,board_y,lens_z],[frame_w/2+cloth_gap,board_y,lens_z],
        [board_x-board_size[0]/2,board_y,board_z+board_standoff+board_tray[2]+board_size[2]]],3);
    cable_path([[board_x,board_y+board_size[1]/2,board_z+35],
        [board_x,175,board_z+35],[monitor_x,175,monitor_z-70],[monitor_x,monitor_y,monitor_z-70]],4,[0.1,0.16,0.25]);
    cable_path([[board_x+board_size[0]/2,board_y,board_z+35],
        [frame_w/2+cloth_gap+cable_lane_w/2,-230,board_z],
        [frame_w/2+cloth_gap+cable_lane_w/2,-230,30]],4,[0.7,0.1,0.12]);
}

module assembly() {
    base_and_frame(); fixtures(); camera_mount(); light_mounts();
    board_mount(); monitor_mount(); curtain_hooks();
    if(show_curtains) curtains();
    if(show_fov) fov_envelope();
    if(show_cables) cable_routes();
    label_xy("COLOR + SIZE / FPGA DEMO",[0,-frame_d/2+45,1],12);
    label_xy("EXTERNAL SERVICE BAY",[monitor_x,-230,1],10);
}

validate_parameters() {
    if(part=="assembly") assembly();
    else if(part=="worktop") {
        fixtures();
        color([0.1,0.65,0.85]) outline(fov_w,fov_d,ref_z+0.5,0.8);
    }
    else if(part=="optics") {
        fixtures(); camera_mount(); light_mounts();
        if(show_fov) fov_envelope();
    }
    else if(part=="camera_plate") camera_plate_part();
    else if(part=="board_tray") board_tray_part();
    else if(part=="monitor_plate") monitor_plate_part();
    else if(part=="light_bracket") light_bracket_part();
    else assert(false,"Unknown part");
}

echo("FRAME_CONCEPT_V1: all hardware sizes are assumptions; not fabrication drawings");
echo(base_mm=[base_w,base_d,base_t],dark_frame_mm=[frame_w,frame_d,frame_h]);
echo(lens_front_to_reference_mm=camera_h,target_fov_mm=[fov_w,fov_d]);
echo(required_full_angles_deg=[2*atan(fov_w/(2*camera_h)),2*atan(fov_d/(2*camera_h))]);
