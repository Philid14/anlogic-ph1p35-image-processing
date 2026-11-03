/*
 FRAME_CONCEPT_V1 — millimetres, degrees; all hardware dimensions ASSUMED.
 Coordinate: X right, Y rear, Z up; fixed tabletop upper surface Z=0.
 Entry point: frame_concept.scad. Edit this file or use OpenSCAD -D overrides.
*/

/* [Scene] */
scene = "color"; // [color,measure,calibration]
part = "assembly"; // [assembly,worktop,optics,camera_plate,board_tray,monitor_plate,light_bracket]
show_curtains = false;
front_open = true;
show_fov = true;
show_cables = true;
show_labels = true;

/* [Frame and base - ASSUMED] */
frame_w = 600;
frame_d = 500;
frame_h = 720; // above fixed tabletop, NOT total height from feet
profile = 20; // solid envelope for 2020 extrusion, grooves omitted
base_margin = 20;
electronics_bay_w = 400;
base_d = 600;
base_t = 18;
foot_h = 30;
insert_w = 360;
insert_d = 240;
insert_t = 3; // reference plane: top of removable carrier

/* [Optical envelope - ASSUMED, NOT SC500CS specification] */
camera_h = 400; // lens FRONT to reference plane, not sensor-to-object WD
camera_min_h = 280;
camera_max_h = 500;
camera_xy = [0,0]; // optical axis offset; keep centered for first build
camera_body = [38,38,16];
lens_d = 18;
lens_len = 20;
camera_standoff = 8;
camera_plate = [90,130,4];
camera_holes = []; // measured PCB hole coordinates relative to optical axis
camera_hole_d = 3.2; // generic clearance; only used if camera_holes is filled
fov_w = 320; // target coverage drawn on reference plane, not predicted optics
fov_d = 180;

/* [Interchangeable fixtures - ASSUMED] */
card_w = 90;
card_d = 110;
card_center_x = 75;
measure_roi = [210,120];
measure_roi_xy = [25,0];
reference_len = 280;
reference_width = 15;
reference_y = -75;
gray_y = 75;
grid_square = 20;
grid_cols = 14; // number of squares, NOT internal corners
grid_rows = 8;

/* [Lighting - ASSUMED] */
light_count = 2; // [1:2]
light_h = 260; // pivot above reference plane
light_x = 225; // absolute X, symmetrical about optical centre
light_len = 200;
light_w = 65;
light_t = 12;
light_tilt = 35; // from DOWNWARD vertical, toward centre; 0=face down

/* [External electronics - ASSUMED] */
board_size = [140,120,18]; // envelope including components, NOT actual board size
board_tray = [170,150,4];
board_standoff = 10;
board_y = 20;
board_z_offset = -30; // tray bottom relative to lens front Z
board_holes = []; // measured [x,y] relative to PCB centre; no fabricated pattern
board_hole_d = 3.2;
cable_lane_w = 30;
cable_pass_w = 45;
cable_pass_h = 25;
connector_keepout = 35; // shaded envelope, not a verified bend radius

/* [Display - ASSUMED; check VESA availability and mass] */
monitor_size = [360,225,35]; // body W,H,T, NOT diagonal size
monitor_gap = 35; // between dark frame right face and display left edge
monitor_y = 205; // front face Y, faces operator at Y negative
monitor_z = 300; // body centre height
vesa = [100,100]; // placeholder, never drill before measurement
vesa_hole_d = 4.5;
monitor_plate_t = 4;
monitor_mass_kg = 2; // design input only; NO structural analysis in this model

/* [Curtains - ASSUMED] */
cloth_gap = 8;
cloth_overlap = 60;
cloth_hem = 25;
cloth_hook_pitch = 120;

/* [Hidden] */
$fn = 28;
eps = 0.1;
ref_z = insert_t;
lens_z = ref_z + camera_h;
camera_plate_z = lens_z + lens_len + camera_body[2] + camera_standoff;
camera_post_y = camera_xy[1] + 65;
camera_post_low = ref_z + camera_min_h + lens_len + camera_body[2] + camera_standoff;
board_x = frame_w/2 + 20 + board_tray[0]/2;
board_z = lens_z + board_z_offset;
monitor_x = frame_w/2 + monitor_gap + monitor_size[0]/2;
monitor_back_y = monitor_y + monitor_size[2];
monitor_plate_y = monitor_back_y + 10;
monitor_post_y = monitor_plate_y + monitor_plate_t + profile/2;
base_left = -frame_w/2-base_margin;
base_right = frame_w/2+electronics_bay_w+base_margin;
base_w = base_right-base_left;
base_cx = (base_right+base_left)/2;
light_z = ref_z + light_h;

module validate_parameters() {
    assert(scene=="color" || scene=="measure" || scene=="calibration", "Unknown scene");
    assert(frame_w>2*profile && frame_d>2*profile && frame_h>200);
    assert(base_t>0 && insert_t>0 && profile>0 && foot_h>=0);
    assert(base_d>=frame_d+2*(cloth_gap+2), "Base too shallow for curtains");
    assert(camera_h>=camera_min_h && camera_h<=camera_max_h, "Camera outside assumed slide range");
    assert(camera_plate_z+camera_plate[2]<frame_h-profile, "Camera collides with roof");
    assert(abs(camera_xy[0])+camera_plate[0]/2<frame_w/2-profile);
    assert(abs(camera_xy[1])+100<frame_d/2-profile);
    assert(fov_w>0 && fov_d>0);
    assert(abs(camera_xy[0])+fov_w/2<=insert_w/2 && abs(camera_xy[1])+fov_d/2<=insert_d/2,
           "Target FOV exceeds removable carrier");
    assert(insert_w<frame_w-2*profile && insert_d<frame_d-2*profile);
    assert(card_center_x+card_w/2<=fov_w/2 && card_d/2<abs(reference_y)-reference_width/2);
    assert(reference_len<=fov_w && abs(reference_y)+reference_width/2<=fov_d/2);
    assert(abs(gray_y)+reference_width/2<=fov_d/2 && card_d/2<abs(gray_y)-reference_width/2);
    assert(abs(measure_roi_xy[0])+measure_roi[0]/2<=fov_w/2 &&
           abs(measure_roi_xy[1])+measure_roi[1]/2<=fov_d/2);
    assert(grid_cols*grid_square<=fov_w && grid_rows*grid_square<=fov_d);
    assert(light_count==1 || light_count==2);
    assert(light_tilt>=0 && light_tilt<=60);
    assert(light_x+light_w/2+light_t<frame_w/2-profile, "Light envelope too wide");
    assert(light_len+30<frame_d-2*profile);
    assert(light_z-light_w/2>ref_z && light_z+light_w/2<lens_z);
    assert(board_tray[0]>board_size[0] && board_tray[1]>board_size[1]);
    assert(board_z>profile && board_z+board_tray[2]+board_standoff+board_size[2]<frame_h);
    assert(board_x+board_tray[0]/2+connector_keepout<base_right, "Electronics bay too narrow");
    assert(abs(board_y)+board_tray[1]/2+connector_keepout<base_d/2);
    assert(monitor_x+monitor_size[0]/2<base_right && monitor_x-monitor_size[0]/2>frame_w/2+cloth_gap);
    assert(monitor_post_y+profile/2<base_d/2 && monitor_z>monitor_size[1]/2);
    assert(monitor_plate_y>board_y+board_tray[1]/2+connector_keepout, "Display blocks board service zone");
    assert(vesa[0]>0 && vesa[1]>0 && vesa[0]+30<monitor_size[0] && vesa[1]+30<monitor_size[1]);
    for(p=camera_holes) assert(abs(p[0])+camera_hole_d<camera_plate[0]/2 && abs(p[1])+camera_hole_d<camera_plate[1]/2);
    for(p=board_holes) assert(abs(p[0])+board_hole_d<board_size[0]/2 && abs(p[1])+board_hole_d<board_size[1]/2);
    children();
}
