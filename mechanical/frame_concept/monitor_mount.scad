module monitor_plate_part() {
    // Local XY plate; assembly rotates it to XZ. Hole pattern is an ASSUMPTION.
    difference() {
        translate([-vesa[0]/2-15,-vesa[1]/2-15,0]) cube([vesa[0]+30,vesa[1]+30,monitor_plate_t]);
        for(x=[-vesa[0]/2,vesa[0]/2],y=[-vesa[1]/2,vesa[1]/2])
            translate([x,y,-eps]) cylinder(d=vesa_hole_d,h=monitor_plate_t+2*eps);
    }
}

module monitor_mount() {
    // Mast loads go into external base, independently of camera roof rails.
    color([0.4,0.44,0.49]) {
        translate([monitor_x-70,monitor_post_y-50,0]) cube([140,85,6]);
        translate([monitor_x-profile/2,monitor_post_y-profile/2,6]) cube([profile,profile,monitor_z+70]);
        translate([monitor_x,monitor_plate_y,monitor_z]) rotate([90,0,0]) monitor_plate_part();
        translate([monitor_x-25,monitor_plate_y-monitor_plate_t,monitor_z-25])
            cube([50,monitor_post_y-monitor_plate_y+monitor_plate_t,50]);
        for(x=[-vesa[0]/2,vesa[0]/2],z=[-vesa[1]/2,vesa[1]/2])
            translate([monitor_x+x,monitor_back_y,monitor_z+z]) rotate([-90,0,0]) cylinder(d=8,h=10);
    }
    color([0.12,0.14,0.18]) translate([monitor_x-monitor_size[0]/2,monitor_y,monitor_z-monitor_size[1]/2])
        cube([monitor_size[0],monitor_size[2],monitor_size[1]]);
    color([0.11,0.31,0.43]) translate([monitor_x-monitor_size[0]/2+12,monitor_y-0.5,monitor_z-monitor_size[1]/2+12])
        cube([monitor_size[0]-24,0.5,monitor_size[1]-24]);
    if(show_labels) color("white") translate([monitor_x,monitor_y-1,monitor_z]) rotate([90,0,0])
        linear_extrude(0.3) text("HDMI / OSD",size=21,halign="center");
}
