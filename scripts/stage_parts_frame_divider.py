"""Stage bounded frame-only unsigned division, never edits formal inputs."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
OUT=ROOT/'tmp/inspection_parts_motion/divider_stage_r1'
SERIAL='''
// Frame-only exact unsigned48/32 division. Start spacing>=50 clocks is a
// contract, NOT a generic pipelined-divider replacement. AWB720-line counter
// guarantees>=720 clocks between complete-frame starts, including bad streams.
// Native reference IP done is49 clocks after its start edge; preserve this.
module awb_frame_divider48(input clk,rst,start,input[47:0]numerator,
 input[31:0]denominator,output reg[47:0]quotient,output reg[31:0]remainder,output reg done);
 reg[47:0]shift;reg[31:0]den,rem;reg[5:0]bit_count;reg busy=0;
 // The official IP only resets its OUTPUT registers. Its in-flight data and
 // start pipeline survive rst. Keep that exact boundary behavior, including
 // a pre-reset operation that completes after rst deasserts. GSR starts0.
 reg[48:0]tokens=49'd0;
 wire[32:0]trial={rem,shift[47]};
 wire subtract=trial>={1'b0,den};
 wire[32:0]difference=trial-{1'b0,den};
 always @(posedge clk)begin
   tokens<={tokens[47:0],start};
   if(start)begin shift<=numerator;den<=denominator;rem<=0;bit_count<=0;busy<=1;end
   else if(busy)begin
    shift<={shift[46:0],subtract};rem<=subtract?difference[31:0]:trial[31:0];
    if(bit_count==47)busy<=0;
    else bit_count<=bit_count+1'b1;
   end
 end
 always @(posedge clk or posedge rst)begin
  if(rst)begin done<=0;quotient<=0;remainder<=0;end
  else begin done<=tokens[48];if(tokens[48])begin quotient<=shift;remainder<=rem;end end
 end
endmodule
'''
def main():
 assert not OUT.exists();(OUT/'isp').mkdir(parents=True)
 s=(HDL/'awb.v').read_text()
 s=s.replace('parameter IMG_WIDTH  = 1920','parameter IMG_WIDTH  = 1920,\n    parameter FRAME_SERIAL_DIV = 0',1)
 begin=s.index('    divider div_gen_G_R_r1 (');end=s.index("    // Preserve the reference",begin)
 original=s[begin:end]
 compact=original.replace('divider div_gen_G_R_r1','awb_frame_divider48 div_gen_G_R_r1').replace('divider divide_G_B_r1','awb_frame_divider48 divide_G_B_r1')
 s=s[:begin]+'    generate if(FRAME_SERIAL_DIV && IMG_HEIGHT>=64)begin:g_frame_divider\n'+compact+'    end else begin:g_streaming_divider\n'+original+'    end endgenerate\n\n'+s[end:]
 (OUT/'awb.v').write_text(s+SERIAL)
 top=(HDL/'isp/isp_top.v').read_text();assert '    .IMG_WIDTH (1280)\n) u_awb' in top
 top=top.replace('    .IMG_WIDTH (1280)\n) u_awb','    .IMG_WIDTH (1280),\n    .FRAME_SERIAL_DIV(1)\n) u_awb',1)
 (OUT/'isp/isp_top.v').write_text(top)
 print('Staged two MAIN files; formal AWB algorithm/parameters and active inputs untouched')
if __name__=='__main__':main()
