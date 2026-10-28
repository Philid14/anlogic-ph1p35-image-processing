if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_01/route.db}
commit_param -step route
phys_opt -post_route -effort high
fix_hold
report_area -io_info -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_03/route.area}
update_timing -mode final
report_timing_status -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_03/route.ts}
report_timing_summary -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_03/route.timing} -ep_num 10 -path_num 1
report_timing_ignored -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_03/ignored.timing}
report_clock_utilization -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_03/clock.txt}
export_db {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_boot_diag_03/route.db}
} message]} {puts "ROUTE_FAILED $message"; exit 1}
puts "ROUTE_COMPLETE_NO_BIT"
exit
