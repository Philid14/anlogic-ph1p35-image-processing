// Icarus cannot execute the encrypted vendor ERAM model. This test-only
// DP/NOREG contract is separately cross-checked against the real native vendor
// model by run_vision_observer.py using identical complete observer vectors.
// NEVER added to the TD project or used as hardware implementation evidence.
module PH1P_LOGIC_ERAM #(
 parameter DATA_WIDTH_A=8,DATA_WIDTH_B=8,ADDR_WIDTH_A=12,ADDR_WIDTH_B=12,
 DATA_DEPTH_A=4096,DATA_DEPTH_B=4096,MODE="DP",CLKMODE="SYNC",REGMODE_A="NOREG",REGMODE_B="NOREG",
 INIT_FILE="NONE",FILL_ALL="NONE",FORCE_KEEP="ON")(
 input clka,cea,ocea,wea,rsta,bea,input[ADDR_WIDTH_A-1:0]addra,input[DATA_WIDTH_A-1:0]dia,
 output reg[DATA_WIDTH_A-1:0]doa,
 input clkb,ceb,oceb,web,rstb,beb,input[ADDR_WIDTH_B-1:0]addrb,input[DATA_WIDTH_B-1:0]dib,
 output reg[DATA_WIDTH_B-1:0]dob,input ecc_sbiterrinj,ecc_dbiterrinj,output ecc_sbiterr,ecc_dbiterr);
 reg[7:0]data[0:4095];
 initial if(DATA_WIDTH_A!=8 || DATA_WIDTH_B!=8 || MODE!="DP" || REGMODE_B!="NOREG")$fatal(1,"Unsupported test ERAM contract");
 always @(posedge clka)if(cea)begin if(wea)data[addra]<=dia;else doa<=data[addra];end
 always @(posedge clkb)if(ceb)dob<=data[addrb];
 assign ecc_sbiterr=0;assign ecc_dbiterr=0;
endmodule
