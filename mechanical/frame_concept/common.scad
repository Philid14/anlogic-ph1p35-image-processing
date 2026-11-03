// Geometry helpers; manufacturing details intentionally omitted.
module beam_between(a,b,w=20) {
    v=b-a; n=norm(v);
    if(n>0) translate(a) rotate(a=acos(v[2]/n),v=[-v[1],v[0],0]+[0,0,0.000001])
        translate([-w/2,-w/2,0]) cube([w,w,n]);
}

module slot_xy(p=[0,0],length=20,d=5,h=5,along_x=true) {
    hull() for(s=[-1,1]) translate([p[0]+(along_x?s*(length-d)/2:0),
          p[1]+(along_x?0:s*(length-d)/2),-eps]) cylinder(d=d,h=h+2*eps);
}

module outline(w,d,z=0,t=1) {
    translate([-w/2,-d/2,z]) render(convexity=4) difference() {
        cube([w,d,t]); translate([t,t,-eps]) cube([w-2*t,d-2*t,t+2*eps]);
    }
}

module label_xy(s,p,size=10,c=[0.1,0.1,0.1]) {
    if(show_labels) color(c) translate(p) linear_extrude(0.25)
        text(s,size=size,halign="center",valign="center",font="Liberation Sans:style=Bold");
}

module cable_path(points,d=3,c=[0.9,0.4,0.08]) {
    color(c) for(i=[0:len(points)-2]) hull() {
        translate(points[i]) sphere(d=d); translate(points[i+1]) sphere(d=d);
    }
}
