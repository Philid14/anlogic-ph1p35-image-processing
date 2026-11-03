// Included by frame_concept.scad; all coordinates reference the optical axis.
module camera_plate_part() {
    difference() {
        translate([-camera_plate[0]/2,-camera_plate[1]/2,0]) cube(camera_plate);
        // Generic rail/clamp slots, NOT asserted to match SC500CS module holes.
        for(x=[-35,35]) slot_xy([x,15],45,5.5,camera_plate[2],false);
        for(p=camera_holes) translate([p[0],p[1],-eps])
            cylinder(d=camera_hole_d,h=camera_plate[2]+2*eps);
    }
}

module camera_mount() {
    color([0.55,0.58,0.62]) {
        // Two X rails fixed to roof side members, Y carriage and rear slide post.
        for(y=[-100,100]) translate([-frame_w/2+profile,camera_xy[1]+y-profile/2,frame_h-profile])
            cube([frame_w-2*profile,profile,profile]);
        translate([camera_xy[0]-profile/2,camera_xy[1]-100,frame_h-profile]) cube([profile,200,profile]);
        translate([camera_xy[0]-profile/2,camera_post_y-profile/2,camera_post_low])
            cube([profile,profile,frame_h-profile-camera_post_low]);
    }
    translate([camera_xy[0],camera_xy[1],camera_plate_z]) color([0.2,0.32,0.43]) camera_plate_part();
    // Clamp block contacts plate edge and slide post. Locking screws symbolic.
    color([0.2,0.32,0.43]) translate([camera_xy[0]-20,camera_post_y-15,camera_plate_z]) cube([40,30,25]);
    color([0.05,0.32,0.23]) translate([camera_xy[0]-camera_body[0]/2,camera_xy[1]-camera_body[1]/2,
        lens_z+lens_len]) cube(camera_body);
    color([0.1,0.1,0.12]) translate([camera_xy[0],camera_xy[1],lens_z]) cylinder(d=lens_d,h=lens_len);
    // Standoffs only rendered at measured holes. Empty default means no fake hole positions.
    for(p=camera_holes) color("silver") translate([camera_xy[0]+p[0],camera_xy[1]+p[1],lens_z+lens_len+camera_body[2]])
        cylinder(d=6,h=camera_standoff);
}

module fov_envelope() {
    // Desired rectangle and illustrative lens cone; not an optical ray trace.
    color([0.12,0.7,0.9,0.09]) hull() {
        translate([camera_xy[0],camera_xy[1],lens_z]) cylinder(d=0.3,h=0.1);
        translate([camera_xy[0]-fov_w/2,camera_xy[1]-fov_d/2,ref_z]) cube([fov_w,fov_d,0.1]);
    }
    color([0.1,0.65,0.85]) translate([camera_xy[0],camera_xy[1],0]) outline(fov_w,fov_d,ref_z+0.4,0.8);
}
