source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display_pr.db}
report_clock_summary -file {D:/anlogic_formal_project/tmp/inspection_parts_motion/full_r3/cdc/clocks.rpt}
report_clock_intersection -file {D:/anlogic_formal_project/tmp/inspection_parts_motion/full_r3/cdc/clock_intersections.rpt}
puts {CDC_GROUP_BEGIN time_gray}
report_nets [get_nets -hier {*latency_tick_gray* *u_latency_timebase*gray*}] -connection -mode final -timing -pin_output_limit 200
puts {CDC_GROUP_END time_gray}
puts {CDC_GROUP_BEGIN held_tuple}
report_nets [get_nets -hier {*latency_selected* *u_latency_slots*selected*}] -connection -mode final -timing -pin_output_limit 200
puts {CDC_GROUP_END held_tuple}
puts {CDC_GROUP_BEGIN select_toggle}
report_nets [get_nets -hier {*latency_select_toggle* *u_latency_slots*select_toggle*}] -connection -mode final -timing -pin_output_limit 200
puts {CDC_GROUP_END select_toggle}
puts {CDC_GROUP_BEGIN read_bad}
report_nets [get_nets -hier {*latency_read_bad* *u_latency_slots*read_bad*}] -connection -mode final -timing -pin_output_limit 200
puts {CDC_GROUP_END read_bad}
puts {CDC_GROUP_BEGIN tagged_fifo_gray}
report_nets [get_nets -hier {*u_video_in*g_tagged*primary_addr_gray_reg*}] -connection -mode final -timing -pin_output_limit 200
puts {CDC_GROUP_END tagged_fifo_gray}
puts {CDC_STRUCTURE_BEGIN}
report_cells [get_cells -hier {*u_latency_capture*time_sync* *u_latency_display*st1* *u_latency_display*st2* *u_latency_display*st3* *u_latency_display*rb1* *u_latency_display*rb2* *u_latency_slots*hb1* *u_latency_slots*hb2* *u_video_in*g_tagged*sync_r1*}] -connection -pin_loc
puts {CDC_STRUCTURE_END}
puts {CDC_AUDIT_COMPLETE}
exit
