if {[catch {
source {D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/settings.cfg}
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/route.db}
clear_sdc
read_sdc {D:/anlogic_formal_project/tmp/style_v2_target_v1/routed_cdc_24/AUDIT_ONLY_NOT_IMPLEMENTED.sdc}
puts "BUNDLE_ROOT_CELLS [llength [get_cells *held_payload*]]"
update_timing -mode final
report_timing_path -from [get_cells *held_payload*] -to [all_registers] -ep_num 2000 -path_num 1 -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/routed_cdc_24/bundle.timing}
report_timing_path -from [all_registers] -to [all_registers] -through [get_nets *cross_inst/primary_addr_gray_reg*] -ep_num 2000 -path_num 1 -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/routed_cdc_24/gray.timing}
report_timing_exception -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/routed_cdc_24/exceptions.timing}
} message]} {puts "AUDIT_FAILED $message"; exit 1}
puts "PHYSICAL_BUNDLE_AUDIT_COMPLETE_NO_DB_EXPORT"
exit
