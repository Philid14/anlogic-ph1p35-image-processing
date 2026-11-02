// Exact current osd_char_lib glyphs, packed into one20K per read port.
// Address starts BEFORE the existing char register; synchronous output meets
// rgb_s1/char_s1 at the existing rendering stage. No extra pixel cycles.
module inspection_font_rom(input clk,input[7:0]character,input[3:0]row,output[15:0]bits);
// ASCII32..95 have unique low-six-bit addresses. The remaining slots hold
// the two Chinese glyphs. No character-range subtractor / priority encoder.
wire[5:0]index=character[7]?{5'b11110,character[0]}:character[5:0];
wire allowed=(!character[7] && (character[6]^character[5]) && character[5:2]!=4'hf) || character[7:1]==7'd64;
reg allowed_d;always @(posedge clk)allowed_d<=allowed;
wire[15:0]raw_bits;assign bits=allowed_d?raw_bits:16'd0;
PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(16),.DATA_WIDTH_B(16),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
 .DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("SP"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
 .INIT_FILE("inspection_font.dath"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_font(
 .clka(clk),.cea(1'b1),.ocea(1'b1),.addra({index,row}),.dia(16'd0),.wea(1'b0),.rsta(1'b0),.bea(1'b1),.doa(raw_bits),
 .clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(10'd0),.dib(16'd0),.web(1'b0),.rstb(1'b0),.beb(1'b0),.dob(),
 .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
endmodule
