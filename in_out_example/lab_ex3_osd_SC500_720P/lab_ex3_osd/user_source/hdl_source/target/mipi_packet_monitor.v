// Passive monitor for this fixed SC500CS RAW10/2-lane format. Uses the same
// observed byte order as the frozen decoder: first header {DT,WClo}, second
// {WChi,ECC}. Checks advertised word count and the physical packet envelope.
// It does NOT claim to check CSI-2 CRC/ECC or analog PHY margin.
module mipi_packet_monitor(
    input clk,rst_n, input hs_valid, input [15:0] hs_data,
    output reg error_pulse, output reg [15:0] error_count
);
    reg previous_valid;
    reg [15:0] first_header;
    reg [10:0] halfwords;
    reg raw_packet, header_bad;
    function [15:0] increment;
        input [15:0] v;
        begin increment=(&v) ? v : v+1'b1; end
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            previous_valid<=0; first_header<=0; halfwords<=0;
            raw_packet<=0; header_bad<=0; error_pulse<=0; error_count<=0;
        end else begin
            previous_valid<=hs_valid; error_pulse<=0;
            if(hs_valid && !previous_valid) begin
                first_header<=hs_data; halfwords<=1;
                raw_packet<=hs_data[15:8]==8'h2b; header_bad<=0;
            end else if(hs_valid) begin
                if(halfwords!=2047) halfwords<=halfwords+1'b1;
                if(halfwords==1 && raw_packet && {hs_data[15:8],first_header[7:0]}!=1600)
                    header_bad<=1;
            end else if(previous_valid && raw_packet && (header_bad || halfwords!=803)) begin
                error_pulse<=1; error_count<=increment(error_count);
            end
        end
    end
endmodule
