// Generated lossless Logo. Official UG1310 PH1P_LOGIC_ERAM, pp13-17.
// Two synchronous reads, same cycles as the inferred implementation.
// prepare_td_runs.py copies the tracked .dath inputs to each TD run.
module target_logo_palette(input clk,input [14:0] address,output wire [24:0] pixel);
wire [13:0] rom_address=(address>=15'd5440 && address<15'd20480) ? address-15'd5440 : 14'd0;
wire [9:0] index;
PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(10),.DATA_WIDTH_B(10),.ADDR_WIDTH_A(14),.ADDR_WIDTH_B(14),
.DATA_DEPTH_A(16384),.DATA_DEPTH_B(16384),.MODE("SP"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
.INIT_FILE("style_logo_index.dath"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_index(
.clka(clk),.cea(1'b1),.ocea(1'b1),.addra(rom_address),.dia(10'd0),.wea(1'b0),.rsta(1'b0),.bea(1'b1),.doa(index),
.clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(14'd0),.dib(10'd0),.web(1'b0),.rstb(1'b0),.beb(1'b0),.dob(),
.ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(25),.DATA_WIDTH_B(25),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
.DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("SP"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
.INIT_FILE("style_logo_palette.dath"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_palette(
.clka(clk),.cea(1'b1),.ocea(1'b1),.addra(index),.dia(25'd0),.wea(1'b0),.rsta(1'b0),.bea(1'b1),.doa(pixel),
.clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(10'd0),.dib(25'd0),.web(1'b0),.rstb(1'b0),.beb(1'b0),.dob(),
.ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
endmodule
