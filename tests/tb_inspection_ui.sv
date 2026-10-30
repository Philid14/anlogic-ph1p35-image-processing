`timescale 1ns/1ps
module tb_inspection_ui;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0,en=0;reg[95:0] rgb=0;
    wire [95:0] out;wire ov,ou,ol;
    color_compare_osd #(.UI_ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.rgb(rgb),
      .valid(v),.user(u),.last(l),.means({24'hb4413c,24'hc84641}),
      .result_valid(1'b1),.sample_id(16'h1234),.display_enable(en),
      .out_rgb(out),.out_valid(ov),.out_user(ou),.out_last(ol));
    reg [95:0] expected0=0,expected1=0;reg ev=0,eu=0,el=0;
    integer fd,n,tv,tu,tl,te,cycles=0,checked=0;
    reg[95:0] din,golden;reg[2047:0] path;
    initial begin
      if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL no vectors");
      fd=$fopen(path,"r");repeat(3)@(negedge clk);rst_n=1;
      while(!$feof(fd))begin
        n=$fscanf(fd,"%d %d %d %d %h %h\n",tv,tu,tl,te,din,golden);
        if(n==6)begin
          @(negedge clk);v=tv;u=tu;l=tl;en=te;rgb=din;
          @(posedge clk);#1;
          if(ov!==ev || ou!==eu || ol!==el)$fatal(1,"FAIL metadata %0d",cycles);
          if(ov)begin
            if(out!==expected0)$fatal(1,"FAIL UI pixel %0d got %h expected %h",cycles,out,expected0);
            checked=checked+1;
          end
          expected0=golden;ev=tv;eu=tu;el=tl;cycles=cycles+1;
        end else if(!$feof(fd))$fatal(1,"FAIL vector format");
      end
      $display("PASS UI transparent overlay, frame enable, glyphs %0d beats",checked);$finish;
    end
endmodule

module tb_inspection_control;
    reg clk=0;always #5 clk=~clk;reg rst_n=0;reg[3:0] sw=0;reg key=1;
    wire[3:0] stable;wire cap,clr;
    inspection_control #(.DEBOUNCE_CYCLES(3),.LONG_CYCLES(9)) dut(
      .clk(clk),.rst_n(rst_n),.switches(sw),.key_n(key),.stable_switches(stable),
      .capture_toggle(cap),.clear_toggle(clr));
    initial begin
      repeat(3)@(negedge clk);rst_n=1;
      sw=15;@(negedge clk);sw=0;repeat(8)@(negedge clk);
      if(stable!==0)$fatal(1,"FAIL switch bounce");
      sw=5;repeat(8)@(negedge clk);if(stable!==5)$fatal(1,"FAIL stable switch");
      key=0;repeat(8)@(negedge clk);key=1;repeat(8)@(negedge clk);
      if(cap!==1 || clr!==0)$fatal(1,"FAIL short key");
      key=0;repeat(22)@(negedge clk);key=1;repeat(8)@(negedge clk);
      if(cap!==1 || clr!==1)$fatal(1,"FAIL long key");
      rst_n=0;repeat(3)@(negedge clk);if(stable!==0 || cap!==0 || clr!==0)$fatal(1,"FAIL reset");
      $display("PASS asynchronous switch debounce, short/long key, reset");$finish;
    end
endmodule
