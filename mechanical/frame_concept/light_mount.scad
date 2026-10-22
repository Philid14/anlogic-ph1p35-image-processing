module light_bracket_part() {
    // Concept L bracket: one pivot hole and two rail slots; not load rated.
    difference() {
        union() {
            cube([35,25,4]); cube([4,25,35]);
        }
        for(y=[7,18]) slot_xy([22,y],16,4.5,4,true);
        translate([-eps,12.5,22]) rotate([0,90,0]) cylinder(d=5.5,h=4+2*eps);
    }
}

module light_mounts() {
    for(i=[0:light_count-1]) let(s=i==0?-1:1) {
        color([0.48,0.52,0.57]) {
            translate([s*(frame_w/2-profile/2)-profile/2,-frame_d/2+profile,light_z-profile/2])
                cube([profile,frame_d-2*profile,profile]);
            for(y=[-light_len/2-12,light_len/2+12]) {
                beam_between([s*light_x,y,light_z],[s*(frame_w/2-profile/2),y,light_z],10);
                translate([s*light_x,y,light_z]) rotate([90,0,0]) cylinder(d=12,h=24,center=true);
            }
        }
        // Emitter is the local -Z face; left and right tilt towards optical axis.
        translate([s*light_x,0,light_z]) rotate([0,s*light_tilt,0]) {
            color([0.7,0.72,0.75]) translate([-light_w/2,-light_len/2,-light_t/2]) cube([light_w,light_len,light_t]);
            color([1,0.96,0.78]) translate([-light_w/2+3,-light_len/2+3,-light_t/2-1]) cube([light_w-6,light_len-6,1]);
        }
        // Aim line to reference plane. It is a setup guide, not illumination simulation.
        if(show_fov) cable_path([[s*light_x,0,light_z],
            [s*(light_x-light_h*tan(light_tilt)),0,ref_z]],1,[0.95,0.65,0.15]);
    }
}
