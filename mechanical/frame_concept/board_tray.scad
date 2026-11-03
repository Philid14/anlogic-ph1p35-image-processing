module board_tray_part() {
    difference() {
        translate([-board_tray[0]/2,-board_tray[1]/2,0]) cube(board_tray);
        for(x=[-board_tray[0]/2+7,board_tray[0]/2-7],y=[-35,35]) slot_xy([x,y],24,4.5,board_tray[2],false);
        for(p=board_holes) translate([p[0],p[1],-eps]) cylinder(d=board_hole_d,h=board_tray[2]+2*eps);
    }
}

module board_mount() {
    // Two detachable cantilever arms connect tray to exterior right service rail.
    color([0.38,0.41,0.45]) {
        translate([frame_w/2-profile, -frame_d/2+profile, board_z-profile])
            cube([profile,frame_d-2*profile,profile]);
        for(y=[board_y-board_tray[1]/2+20,board_y+board_tray[1]/2-20])
            translate([frame_w/2-profile,y-profile/2,board_z-profile])
                cube([board_x+board_tray[0]/2-frame_w/2+profile,profile,profile]);
    }
    translate([board_x,board_y,board_z]) color([0.55,0.62,0.67]) board_tray_part();
    color([0.08,0.4,0.26]) translate([board_x-board_size[0]/2,board_y-board_size[1]/2,
        board_z+board_tray[2]+board_standoff]) cube(board_size);
    for(p=board_holes) color("silver") translate([board_x+p[0],board_y+p[1],board_z+board_tray[2]])
        cylinder(d=6,h=board_standoff);
    // Service/bend envelope, not a physical enclosure. No electrical connector assignment.
    color([0.95,0.55,0.12,0.08]) translate([board_x-board_tray[0]/2-connector_keepout,
        board_y-board_tray[1]/2-connector_keepout,board_z+board_tray[2]])
        cube([board_tray[0]+2*connector_keepout,board_tray[1]+2*connector_keepout,board_standoff+board_size[2]+20]);
    label_xy("FPGA SERVICE",[board_x,board_y,board_z+board_tray[2]+board_standoff+board_size[2]+1],9,[1,1,1]);
}
