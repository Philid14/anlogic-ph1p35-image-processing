// Explicit operator choice for known round parts, not automatic arc fitting.
// One long-press toggle, irrespective of the original hold-repeat events.
module inspection_shape_select(input clk,rst_n,enable,long_toggle,frame_start,
 output reg result_circle);
 reg seen,circle,frame_circle;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin seen<=0;circle<=0;frame_circle<=0;result_circle<=0;end
  else begin
   seen<=long_toggle;
   if(enable && long_toggle!=seen)circle<=!circle;
   if(frame_start)begin frame_circle<=circle;result_circle<=frame_circle;end
  end
 end
endmodule
