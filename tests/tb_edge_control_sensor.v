`timescale 1ns / 1ps
// Functional configuration-sequencer test; bus stub ACKs each write.
// This is not a physical I2C ACK/readback test.
module tb_edge_control_sensor;
    reg clk=0,rst_n=0;
    always #2 clk=~clk;
    reg [1:0] keys=3;
    wire [8:0] requested;
    wire cfg_done,ae_done,scl;
    tri sda;
    wire ae_req=1'b0; // verified against actual Top by the Python runner
    edge_key_control #(.DEBOUNCE_CYCLES(3),.LONG_CYCLES(8)) controls (
        .clk(clk),.rst_n(rst_n),.keys_n(keys),.requested_config(requested));
    uicfgcs500_720p sensor (.I_clk(clk),.I_rst_n(rst_n),
        .I_ae_req(ae_req),.I_ae(16'd1990),.I_ag(16'd0),
        .O_cam_scl(scl),.IO_cam_sda(sda),.O_cfg_done(cfg_done),.O_ae_cfg_done(ae_done));
    integer i,initial_writes;
    initial begin
        repeat(10) @(negedge clk);rst_n=1;
        wait(cfg_done);@(negedge clk);initial_writes=sensor.u_i2c.writes;
        if(sensor.u_i2c.gain_coarse!==8'h1f || sensor.u_i2c.gain_fine!==8'h3f)
            $fatal(1,"FAIL frozen analog gain init");
        if({sensor.u_i2c.exp0[3:0],sensor.u_i2c.exp1,sensor.u_i2c.exp2[7:4]}!==16'd1990)
            $fatal(1,"FAIL frozen exposure init");
        if({sensor.u_i2c.vts0,sensor.u_i2c.vts1}!==16'd1000 ||
           {sensor.u_i2c.hts0,sensor.u_i2c.hts1}!==16'd1600)
            $fatal(1,"FAIL frozen VTS/HTS init");
        for(i=0;i<50;i=i+1) begin
            keys=0;repeat(30) @(negedge clk);
            keys=3;repeat(30) @(negedge clk);
        end
        if(sensor.u_i2c.writes != initial_writes || !ae_done || ae_req)
            $fatal(1,"FAIL keys triggered sensor rewrite");
        $display("PASS checkpoint_A sensor: %0d initial writes, exposure1990 VTS1000 HTS1600 gain1f/3f, no writes after 50 key sequences",initial_writes);
        $finish;
    end
    initial begin repeat(400000) @(posedge clk);$fatal(1,"FAIL sensor init timeout");end
endmodule
module uii2c #(parameter WMEN_LEN=4,RMEN_LEN=1,CLK_DIV=239)(
    input I_clk,I_rstn,input [31:0] I_wr_data,input [7:0] I_wr_cnt,I_rd_cnt,
    input I_iic_mode,I_iic_req,output O_iic_scl,inout IO_iic_sda,
    output [7:0] O_rd_data,output reg O_iic_busy
);
    reg [3:0] busy_count;
    reg [7:0] gain_coarse,gain_fine,exp0,exp1,exp2,vts0,vts1,hts0,hts1;
    integer writes=0;
    assign O_iic_scl=1;assign IO_iic_sda=1'bz;assign O_rd_data=0;
    always @(posedge I_clk) begin
        if(!I_rstn) begin O_iic_busy<=0;busy_count<=0;writes<=0;end
        else if(!O_iic_busy && I_iic_req) begin
            O_iic_busy<=1;busy_count<=5;writes<=writes+1;
            case({I_wr_data[15:8],I_wr_data[23:16]})
                16'h3e08:gain_coarse<=I_wr_data[31:24];
                16'h3e09:gain_fine<=I_wr_data[31:24];
                16'h3e00:exp0<=I_wr_data[31:24];
                16'h3e01:exp1<=I_wr_data[31:24];
                16'h3e02:exp2<=I_wr_data[31:24];
                16'h320e:vts0<=I_wr_data[31:24];
                16'h320f:vts1<=I_wr_data[31:24];
                16'h320c:hts0<=I_wr_data[31:24];
                16'h320d:hts1<=I_wr_data[31:24];
            endcase
        end else if(O_iic_busy) begin
            if(busy_count==0) O_iic_busy<=0;
            else busy_count<=busy_count-1'b1;
        end
    end
endmodule
