// MAIN fixed-platform measurement, parallel to the unmodified video path.
// Both patches are measured in the SAME complete post-AWB/pre-effect frame.
// Results are published at the NEXT early SOF, never by gating video/FIFO I/O.
module color_compare_stats #(
    parameter integer WIDTH=1280, HEIGHT=720,
    parameter integer REF_X=256, TEST_X=896, ROI_Y=256,
    parameter integer W_LOG=7, H_LOG=7
)(
    input clk,rst_n,input [95:0] rgb,input valid,user,last,
    output reg [47:0] means, output reg result_valid,
    output reg [15:0] sample_id
);
    localparam integer N_LOG=W_LOG+H_LOG, SW=8+N_LOG;
    localparam integer RW=1<<W_LOG, RH=1<<H_LOG, N=1<<N_LOG;
    reg [10:0] x;
    reg [9:0] y;
    reg armed,bad,finished;
    reg [17:0] beats;
    reg [15:0] sequence_id;
    reg [N_LOG:0] count_ref,count_test;
    reg [SW-1:0] sum_ref[0:2],sum_test[0:2];
    wire [10:0] px=user?11'd0:x;
    wire [9:0] py=user?10'd0:y;
    wire hit_y=py>=ROI_Y && py<ROI_Y+RH;
    wire hit_ref=hit_y && px>=REF_X && px<REF_X+RW;
    wire hit_test=hit_y && px>=TEST_X && px<TEST_X+RW;
    wire geometry_error=last!=(px==WIDTH-4);
    wire [9:0] total[0:2];
    genvar c;
    generate for(c=0;c<3;c=c+1)begin:g_sum
        assign total[c]=({2'b0,rgb[95-8*c -:8]}+{2'b0,rgb[71-8*c -:8]})+
                        ({2'b0,rgb[47-8*c -:8]}+{2'b0,rgb[23-8*c -:8]});
    end endgenerate
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            x<=0;y<=0;armed<=0;bad<=0;finished<=0;beats<=0;
            sequence_id<=0;sample_id<=0;means<=0;result_valid<=0;
            count_ref<=0;count_test<=0;
            for(i=0;i<3;i=i+1)begin sum_ref[i]<=0;sum_test[i]<=0;end
        end else begin
            if(user)begin
                result_valid<=armed && finished && !bad &&
                    beats==(WIDTH/4)*HEIGHT && count_ref==N && count_test==N;
                sample_id<=sequence_id;sequence_id<=sequence_id+1'b1;
                for(i=0;i<3;i=i+1)begin
                    means[47-8*i -:8]<=(sum_ref[i]+(1<<(N_LOG-1)))>>N_LOG;
                    means[23-8*i -:8]<=(sum_test[i]+(1<<(N_LOG-1)))>>N_LOG;
                    sum_ref[i]<=valid && hit_ref ? total[i] : 0;
                    sum_test[i]<=valid && hit_test ? total[i] : 0;
                end
                count_ref<=valid && hit_ref ? 4 : 0;
                count_test<=valid && hit_test ? 4 : 0;
                armed<=1;finished<=0;bad<=valid && geometry_error;
                beats<=valid?1:0;
                x<=valid ? ((WIDTH==4)?0:4) : 0;
                y<=valid && WIDTH==4 ? 1 : 0;
            end else if(valid)begin
                if(!armed || finished || geometry_error)bad<=1;
                if(beats<(WIDTH/4)*HEIGHT+1)beats<=beats+1'b1;
                x<=px==WIDTH-4?0:px+4;
                if(px==WIDTH-4)y<=py+1'b1;
                if(px==WIDTH-4 && py==HEIGHT-1)finished<=1;
                if(hit_ref)begin
                    if(count_ref<N)count_ref<=count_ref+4;else bad<=1;
                    for(i=0;i<3;i=i+1)sum_ref[i]<=sum_ref[i]+total[i];
                end
                if(hit_test)begin
                    if(count_test<N)count_test<=count_test+4;else bad<=1;
                    for(i=0;i<3;i=i+1)sum_test[i]<=sum_test[i]+total[i];
                end
            end else if(last)bad<=1;
        end
    end
endmodule
