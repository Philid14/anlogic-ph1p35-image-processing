`timescale 1ns/1ps
module tb_alignment_storage #(parameter WIDTH=68,HEIGHT=9,SPATIAL_ONLY=0);
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg[18:0] requested_config=0;reg[31:0] I_fifo_event_counts=0;
    reg[95:0] I_data=0;reg I_valid=0,I_user=0,I_last=0;reg O_ready=1;
    wire[95:0] data_new,data_old;wire valid_new,user_new,last_new,ready_new;
    wire valid_old,user_old,last_old,ready_old;
    edge_control_stream #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT),.DENOISE_ENABLE(!SPATIAL_ONLY),.NMS_ENABLE(!SPATIAL_ONLY),.QUALITY_ENABLE(!SPATIAL_ONLY),.TEMPORAL_ENABLE(!SPATIAL_ONLY),.RELIABILITY_ENABLE(1)) dut(
        .clk(clk),.rst_n(rst_n),.requested_config(requested_config),.I_fifo_event_counts(I_fifo_event_counts),
        .I_data(I_data),.I_valid(I_valid),.I_user(I_user),.I_last(I_last),.O_ready(O_ready),
        .O_data(data_new),.O_valid(valid_new),.O_user(user_new),.O_last(last_new),.I_ready(ready_new));
    edge_control_reference #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT),.DENOISE_ENABLE(!SPATIAL_ONLY),.NMS_ENABLE(!SPATIAL_ONLY),.QUALITY_ENABLE(!SPATIAL_ONLY),.TEMPORAL_ENABLE(!SPATIAL_ONLY),.RELIABILITY_ENABLE(1)) reference_dut(
        .clk(clk),.rst_n(rst_n),.requested_config(requested_config),.I_fifo_event_counts(I_fifo_event_counts),
        .I_data(I_data),.I_valid(I_valid),.I_user(I_user),.I_last(I_last),.O_ready(O_ready),
        .O_data(data_old),.O_valid(valid_old),.O_user(user_old),.O_last(last_old),.I_ready(ready_old));
    reg[31:0] random_state=32'h5079213d;
    integer checks=0,f,y,b,n,mode;
    reg [7:0] threshold;
    task cycle;
        begin
            random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};
            I_data={random_state,~random_state,{random_state[15:0],random_state[31:16]}};
            I_fifo_event_counts=random_state;
            @(posedge clk);#1;checks=checks+1;
            if({data_new,valid_new,user_new,last_new,ready_new} !== {data_old,valid_old,user_old,last_old,ready_old})
                $fatal(1,"alignment differs f=%0d y=%0d beat=%0d check=%0d new=%h old=%h",f,y,b,checks,data_new,data_old);
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(7)cycle;rst_n=1;repeat(3)cycle;
        for(f=0;f<25;f=f+1)begin
            mode=(f%2) ? 4 : f%5;
            threshold=10+f*10;
            requested_config={mode[2:0],threshold,8'd130};
            I_user=1;I_valid=0;I_last=0;cycle;I_user=0;
            repeat(f%4)cycle;
            for(y=0;y<HEIGHT;y=y+1)begin
                for(b=0;b<WIDTH/4;b=b+1)begin
                    if(y==HEIGHT/2 && b==WIDTH/8 && f==11)begin
                        rst_n=0;repeat(3)cycle;rst_n=1;
                    end
                    I_valid=1;I_last=(b==WIDTH/4-1);cycle;
                    if((b+y+f)%13==0)begin I_valid=0;I_last=0;cycle;end
                end
                I_valid=0;I_last=0;
                // Requests outside SOF must not relabel a pixel or a frame.
                requested_config=random_state[18:0];repeat(3+y%4)cycle;
            end
            repeat(35+f%5)cycle;
        end
        I_valid=0;I_user=0;I_last=0;repeat(64)cycle;
        $display("PASS ALIGNMENT_STORAGE checks=%0d width=%0d height=%0d",checks,WIDTH,HEIGHT);$finish;
    end
endmodule
