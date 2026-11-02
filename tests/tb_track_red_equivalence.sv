`timescale 1ns/1ps
module tb_track_red_equivalence;
 reg[7:0]r=0,g=0,base=0;
 wire[3:0]oldhit,newhit;wire[7:0]limit=r-(r>>2);
 genvar k;
 generate for(k=0;k<4;k=k+1)begin:lane
  wire[7:0]b=base+k;
  wire raw;
  color_classify #(.TARGET_CLASS(0),.HUE_HALF_WIDTH_DEG(30),.C_MIN(24),.V_MIN(32)) reference(
   .I_r(r),.I_g(g),.I_b(b),.O_hit(raw));
  assign oldhit[k]=raw && g<=limit && b<=limit;
  vision_red_classify compact(.r(r),.g(g),.b(b),.hit(newhit[k]));
 end endgenerate
 integer ri,gi,bi;
 initial begin
  for(ri=0;ri<256;ri=ri+1)begin
   r=ri;
   for(gi=0;gi<256;gi=gi+1)begin
    g=gi;
    for(bi=0;bi<256;bi=bi+4)begin
     base=bi;#1;
     if(oldhit!==newhit)$fatal(1,"RGB exhaustive mismatch R%0d G%0d Bbase%0d old%h new%h",ri,gi,bi,oldhit,newhit);
    end
   end
  end
  $display("PASS exhaustive16777216 RGB888 values: specialized red predicate equals unchanged TARGET W30/C24/V32 plus relative channel dominance");$finish;
 end
endmodule
