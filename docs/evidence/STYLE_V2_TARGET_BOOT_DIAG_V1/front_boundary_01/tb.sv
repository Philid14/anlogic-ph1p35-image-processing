`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0; always #8.334 clk=~clk;
reg rv=0,rs=0,rl=0,fe=0; reg [39:0] raw={4{10'd400}};
wire [127:0] rgb128; wire dv,du,dl; wire [95:0] rgb;
wire av,au,al; wire [95:0] ar;
demosaic #(.IMG_WIDTH(1280),.IMG_HEIGHT(720),.data_complete_delay(50),.BAYER_MODE("BGGR")) dm(
.I_clk(clk),.I_rst_n(rst_n),.axi4s_video_tdata(raw),.axi4s_video_tdest(10'd0),
.axi4s_video_tlast(rl),.axi4s_video_tvalid(rv),.axi4s_video_tuser(rs),.axi4s_video_tready(),
.O_tlast(dl),.O_tuser(du),.O_tdata(rgb128),.O_tvalid(dv),.O_tready(1'b1));
data128_96 cv(.I_tdata(rgb128),.O_tdata(rgb));
awb #(.IMG_WIDTH(1280),.IMG_HEIGHT(720)) aw(.I_clk(clk),.I_rst_n(rst_n),.I_tlast(dl),.I_tuser(du),
.I_tdata(rgb),.I_tvalid(dv),.I_tready(),.O_tlast(al),.O_tuser(au),.O_tdata(ar),.O_tvalid(av),.O_tready(1'b1));
wire cap,pv,s,e,ef,abort,rc,rg,od,og,epoch;wire [15:0] re,oe;
target_observer_adapter obs(.clk(clk),.rst_n(rst_n),.control_session(32'd1),.session_ready(1'b1),
.now_tick(64'd100),.time_valid(1'b1),.raw_valid(rv),.raw_sof(rs),.raw_eol(rl),.native_frame_end(fe),
.awb_user(au),.awb_valid(av),.awb_last(al),.awb_rgb(ar),.external_error(1'b0),
.capture_start(cap),.pixel_valid(pv),.sof(s),.eol(e),.eof(ef),.frame_abort(abort),
.raw_complete(rc),.raw_good(rg),.observer_done(od),.observer_good(og),.epoch_fault(epoch),
.raw_error_count(re),.observer_error_count(oe));
integer cy=0,f,y,x,nb=0,nr=0,ng=0,nu=0,nl=0,bad=0;
always @(negedge clk) if(rst_n) begin
 f=cy/500000;y=(cy%500000)/500;x=cy%500;
 rv=f<2 && y<720 && x<400 && x%5!=4;rs=rv && y==0 && x==0;rl=rv && x==398;
 fe=f<2 && y==720 && x==0;cy=cy+1;
 if(cy==1000000) begin $display("RESULT AWB beats=%0d user=%0d last=%0d raw_good=%0d obs_done=%0d obs_good=%0d abort_beats=%0d epoch=%b rawerr=%0d obserr=%0d",nb,nu,nl,nr,ng,bad,ba,epoch,re,oe);$finish;end
end
integer ba=0;
always @(posedge clk) begin
 if(av)nb=nb+1;if(au)begin nu=nu+1;$display("AWB_USER cycle=%0d raw_identity=%b rawframe=%d",cy,obs.identity_valid,obs.capture_frame);end
 if(al)nl=nl+1;if(rc)begin nr=nr+rg;$display("RAW_COMPLETE cycle=%0d good=%b rawbeats=%d",cy,rg,obs.raw_beats);end
 if(od)begin ng=ng+1;bad=bad+og;$display("OBSERVER_DONE cycle=%0d good=%b obsbeats=%d bad=%b",cy,og,obs.obs_beats,obs.obs_bad);end
 if(pv&&abort)ba=ba+1;
end
initial begin #100;rst_n=1;end
initial begin #18000000;$fatal(1,"timeout");end
endmodule
// Timing-boundary experiment only. Divider arithmetic does not drive AWB valid/user/last;
// actual demosaic/line buffers/signal_delay/observer RTL and native vendor RAM remain.
module divider(input clk,rst,start,input [31:0] denominator,input [47:0] numerator,output reg done,output reg [47:0] quotient);
always @(posedge clk) begin done<=start;quotient<=48'h10000;end
endmodule
