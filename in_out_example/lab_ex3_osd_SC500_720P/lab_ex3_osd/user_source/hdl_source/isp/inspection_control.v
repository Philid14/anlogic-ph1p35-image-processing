// Human controls synchronized/debounced in the existing CSI domain.
// SW0 color; SW1 dimension; SW2 bright foreground; SW3 calibration mode.
// Independent stable levels, then the consumer latches them at SOF.
module inspection_control #(
    parameter integer DEBOUNCE_CYCLES=1200000,
    parameter integer LONG_CYCLES=42000000,
    parameter integer REPEAT_CYCLES=6000000
)(input clk,rst_n,input [3:0] switches,input key_n,
  output reg [3:0] stable_switches,output reg capture_toggle,clear_toggle,
  output reg repeat_toggle);
    localparam N=DEBOUNCE_CYCLES>1?$clog2(DEBOUNCE_CYCLES):1;
    (* async_reg="true" *) reg [3:0] meta,sync;
    reg [N-1:0] counts[0:3];
    localparam R=REPEAT_CYCLES>1?$clog2(REPEAT_CYCLES):1;
    reg [R-1:0] repeat_count;
    reg repeating;
    (* async_reg="true" *) reg key_meta,key_sync;
    wire short_event,long_event;
    edge_key_event #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES),.LONG_CYCLES(LONG_CYCLES)) u_key(
        .clk(clk),.rst_n(rst_n),.key_n(key_n),.press(),
        .short_release(short_event),.long_press(long_event));
    integer k;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            meta<=0;sync<=0;stable_switches<=0;capture_toggle<=0;clear_toggle<=0;
            key_meta<=1;key_sync<=1;repeating<=0;repeat_count<=0;repeat_toggle<=0;
            for(k=0;k<4;k=k+1)counts[k]<=0;
        end else begin
            meta<=switches;sync<=meta;
            key_meta<=key_n;key_sync<=key_meta;
            for(k=0;k<4;k=k+1)begin
                if(sync[k]==stable_switches[k])counts[k]<=0;
                else if(counts[k]==DEBOUNCE_CYCLES-1)begin
                    stable_switches[k]<=sync[k];counts[k]<=0;
                end else counts[k]<=counts[k]+1'b1;
            end
            if(short_event)capture_toggle<=!capture_toggle;
            if(key_sync)begin repeating<=0;repeat_count<=0;end
            else if(repeating)begin
                if(repeat_count==REPEAT_CYCLES-1)begin
                    repeat_count<=0;repeat_toggle<=!repeat_toggle;
                end else repeat_count<=repeat_count+1'b1;
            end
            if(long_event)begin
                clear_toggle<=!clear_toggle;repeat_toggle<=!repeat_toggle;
                repeating<=1;repeat_count<=0;
            end
        end
    end
endmodule
