if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display_pr.db}
phys_opt -post_route -effort high
fix_hold
report_area -io_info -file {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/route.area}
update_timing -mode final
report_timing_status -file {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/route.ts}
report_timing_summary -file {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/route.timing} -ep_num 10 -path_num 1
report_timing_ignored -file {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/ignored.timing}
report_timing_exception -file {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/exceptions.timing}
report_clock_utilization -file {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/clock.txt}
export_db {D:/anlogic_formal_project/tmp/color_compare_v1/r0/polish01/route.db}
} msg]} {puts "POLISH_FAILED $msg";exit 1}
puts "POLISH_COMPLETE_NO_BIT"
exit
