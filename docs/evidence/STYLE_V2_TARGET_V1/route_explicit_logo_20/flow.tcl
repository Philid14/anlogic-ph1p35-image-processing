if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/anlogic_formal_project/tmp/style_v2_target_v1/place_explicit_logo_20/place.db}
commit_param -step route
route
report_area -io_info -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/route.area}
update_timing -mode final
report_timing_status -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/route.ts}
report_timing_summary -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/route.timing} -ep_num 10 -path_num 1
report_timing_ignored -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/ignored.timing}
report_clock_utilization -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/clock.txt}
export_db {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/route.db}
} message]} {puts "ROUTE_FAILED $message"; exit 1}
puts "ROUTE_COMPLETE_NO_BIT"
exit
