`timescale 1ns/1ps
module tb_engineering_dimension;
    reg [10:0] x;reg [9:0] y;reg cal,scaled,present,ready;
    reg[2:0] status;reg[43:0] box,coords;reg[1:0] gaps;reg[79:0] digits;
    wire[3:0] marks;wire text_valid;wire[7:0] character;wire[3:0] row,col;wire[15:0] bits;
    engineering_dimension_marks dut(.x(x),.y(y),.cal(cal),.calibrated(scaled),
      .object_valid(present),.formatted(ready),.cal_status(status),.box_coords(box),.gap_coords(coords),
      .gap_valid(gaps),.digits(digits),.marks(marks),.text_valid(text_valid),.character(character),.glyph_row(row),.glyph_col(col));
    osd_char_lib font(.I_char(character),.I_row(row),.O_row_bits(bits));
    integer fd,n,ix,iy,ic,is,ip,ir,ist,ig,expected,k,got,checks=0;reg[2047:0] path;
    initial begin
        if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL no vectors");fd=$fopen(path,"r");
        while(!$feof(fd))begin
            n=$fscanf(fd,"%d %d %d %d %d %d %d %h %h %d %h %h\n",ix,iy,ic,is,ip,ir,ist,box,coords,ig,digits,expected);
            if(n==12)begin
                x=ix;y=iy;cal=ic;scaled=is;present=ip;ready=ir;status=ist;gaps=ig;#1;
                got=0;
                for(k=0;k<4;k=k+1)if(marks[3-k] || (text_valid && bits[15-col-k]))got=got|(1<<(3-k));
                if(got!==expected)$fatal(1,"FAIL drawing (%0d,%0d) got%h expected%h char%h row%0d col%0d",ix,iy,got,expected,character,row,col);
                checks=checks+1;
            end else if(!$feof(fd))$fatal(1,"FAIL format");
        end
        $display("PASS engineering drawing %0d four-pixel positions",checks);$finish;
    end
endmodule
