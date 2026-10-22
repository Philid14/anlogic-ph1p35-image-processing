if {[catch {
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
analyze -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/logo_mapping_isolated_14/current/target_logo_palette.v}
elaborate -top target_logo_palette
optimize_rtl
report_area -file logo_rtl.area
optimize_gate -packarea logo_gate.area
export_db logo_gate.db
} message]} {puts "ISOLATED_SYN_FAILED $message";exit 1}
puts "ISOLATED_ROM_SYN_COMPLETE_NO_BOARD_TIMING_NO_BIT"
exit
