"""One-time replacement of resettable register metadata with exact native RAM taps."""
from pathlib import Path
R=Path(__file__).resolve().parents[1];H=R/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
p=H/'isp/edge_control_stream.v';s=p.read_text().replace('reg [18:0] config_p','wire [18:0] config_p').replace('reg [3:0] ui_pipe','wire [3:0] ui_pipe')
start=s.index('    // Like RGB payload, delayed config');end=s.index('    wire [95:0] edge_data',start);s=s[:start]+s[end:]
start=s.index('    generate if(INSPECTION_V5)begin:g_ui_shift');end=s.index('    wire [95:0] compare_data',start)
s=s[:start]+'''    generate if(INSPECTION_V5)begin:g_config_ram
        wire[22:0] first,spatial,final_config;
        inspection_config_delay #(.TAP(SPATIAL_STAGES),.DEPTH(EDGE_STAGES)) u_delay(
            .clk(clk),.rst_n(rst_n),.data({ui_beat,beat_config}),
            .first(first),.spatial(spatial),.final_data(final_config));
        for(genvar c=0;c<EDGE_STAGES;c=c+1)begin:g_taps
            assign config_p[c]=c==0?first[18:0]:c==SPATIAL_STAGES-1?spatial[18:0]:c==EDGE_STAGES-1?final_config[18:0]:19'd0;
            assign ui_pipe[c]=c==0?first[22:19]:c==EDGE_STAGES-1?final_config[22:19]:4'd0;
        end
    end else begin:g_config_legacy
        reg[18:0] cp[0:EDGE_STAGES-1];reg[3:0] sp[0:EDGE_STAGES-1];integer ci;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)for(ci=0;ci<EDGE_STAGES;ci=ci+1)begin cp[ci]<=RESET_CONFIG;sp[ci]<=0;end
            else begin cp[0]<=beat_config;sp[0]<=ui_beat;
                for(ci=1;ci<EDGE_STAGES;ci=ci+1)begin cp[ci]<=cp[ci-1];sp[ci]<=sp[ci-1];end
            end
        end
        for(genvar c=0;c<EDGE_STAGES;c=c+1)begin:g_taps assign config_p[c]=cp[c];assign ui_pipe[c]=sp[c];end
    end endgenerate
'''+s[end:];p.write_text(s)
p=R/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al';s=p.read_text()
import re
entry=re.search(r'\s*<File Path="[^\"]*measure_background.v"[\s\S]*?</File>',s).group()
s=s.replace(entry,entry+entry.replace('measure_background.v','inspection_config_delay.v').replace('181','182'));p.write_text(s)
for name in ('run_inspection_legacy.py','run_inspection_integrated.py','run_inspection_track.py','run_inspection_reset.py'):
 p=R/'tests'/name;s=p.read_text().replace("HDL/'vision/measure_background.v']","HDL/'vision/measure_background.v',HDL/'vision/inspection_config_delay.v']");p.write_text(s)
p=R/'scripts/build_inspection_shape_track.py';s=p.read_text().replace('full_r2','full_r3').replace('len(entries)==84','len(entries)==85').replace("HDL+'vision/measure_background.v'}","HDL+'vision/measure_background.v',HDL+'vision/inspection_config_delay.v'}")
s=s.replace("'tmp/inspection_shape_track/integrated')","'tmp/inspection_shape_track/integrated','tmp/inspection_shape_track/reset','tmp/inspection_shape_track/config','tmp/inspection_shape_track/background_full')")
p.write_text(s)
