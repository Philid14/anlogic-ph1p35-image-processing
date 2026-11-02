// Exact current osd_char_lib glyphs, packed into one20K per read port.
// Address starts BEFORE the existing char register; synchronous output meets
// rgb_s1/char_s1 at the existing rendering stage. No extra pixel cycles.
module inspection_font_rom(input clk,input[7:0]character,input[3:0]row,output[15:0]bits);
reg[5:0]index;
always @*begin
 index=0;
 if(character>=48 && character<=57)index=character-47;
 else if(character>=65 && character<=90)index=character-54;
 else case(character)
 43:index=37;45:index=38;46:index=39;47:index=40;58:index=41;
 128:index=42;129:index=43;default:index=0;
 endcase
end
PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(16),.DATA_WIDTH_B(16),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
 .DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("SP"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
 .INIT_FILE("inspection_font.dath"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_font(
 .clka(clk),.cea(1'b1),.ocea(1'b1),.addra({index,row}),.dia(16'd0),.wea(1'b0),.rsta(1'b0),.bea(1'b1),.doa(bits),
 .clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(10'd0),.dib(16'd0),.web(1'b0),.rstb(1'b0),.beb(1'b0),.dob(),
 .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
endmodule
