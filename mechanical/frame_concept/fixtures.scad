module fixtures() {
    color([0.48,0.49,0.49]) translate([-insert_w/2,-insert_d/2,0]) cube([insert_w,insert_d,insert_t]);
    // Three edge stops form a repeatable carrier seat; no arbitrary drilled grid.
    color([0.2,0.23,0.26]) {
        for(x=[-insert_w/3,insert_w/3]) translate([x-12,insert_d/2,0]) cube([24,6,8]);
        translate([-insert_w/2-6,-12,0]) cube([6,24,8]);
    }
    if(scene=="color") {
        for(s=[-1,1]) {
            color(s<0?[0.74,0.22,0.17]:[0.64,0.25,0.18])
                translate([s*card_center_x-card_w/2,-card_d/2,ref_z]) cube([card_w,card_d,0.4]);
            label_xy(s<0?"STANDARD":"SAMPLE",[s*card_center_x,0,ref_z+0.5],8,[1,1,1]);
        }
    }
    if(scene=="measure") {
        color([0.12,0.68,0.55]) translate([measure_roi_xy[0],measure_roi_xy[1],0])
            outline(measure_roi[0],measure_roi[1],ref_z+0.4,0.8);
        // Silhouette samples: top surfaces are NOT on the reference plane.
        color([0.75,0.77,0.8]) {
            translate([-65,-30,ref_z]) cube([90,60,5]);
            translate([80,0,ref_z]) render(convexity=4) difference() { cylinder(d=50,h=5); translate([0,0,-eps]) cylinder(d=24,h=5+2*eps); }
        }
        color([0.88,0.89,0.9]) translate([-140,-65,ref_z]) cube([20,130,0.3]);
        for(y=[-60:10:60]) color([0.1,0.1,0.1]) translate([-140,y,ref_z+0.3]) cube([10,0.5,0.2]);
        label_xy("SIZE / CALIBRATION",[0,insert_d/2-18,ref_z+0.5],9);
    }
    if(scene=="calibration") {
        for(x=[0:grid_cols-1],y=[0:grid_rows-1]) color((x+y)%2==0?[0.92,0.92,0.9]:[0.04,0.04,0.04])
            translate([(x-grid_cols/2)*grid_square,(y-grid_rows/2)*grid_square,ref_z]) cube([grid_square,grid_square,0.2]);
    } else {
        color([0.72,0.73,0.71]) translate([-reference_len/2,gray_y-reference_width/2,ref_z]) cube([reference_len,reference_width,0.3]);
        label_xy("GRAY / WHITE REF",[0,gray_y,ref_z+0.4],6);
        color([0.86,0.87,0.85]) translate([-reference_len/2,reference_y-reference_width/2,ref_z]) cube([reference_len,reference_width,0.3]);
        for(x=[-reference_len/2:10:reference_len/2]) color([0.1,0.1,0.1])
            translate([x,reference_y-reference_width/2,ref_z+0.3]) cube([0.5,5,0.2]);
    }
}
