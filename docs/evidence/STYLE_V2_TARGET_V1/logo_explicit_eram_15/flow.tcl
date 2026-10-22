if {[catch {
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
analyze -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/logo_explicit_eram_15/target_logo_palette.v}
elaborate -top target_logo_palette
optimize_rtl
report_area -file logo_rtl.area
optimize_gate -packarea logo_gate.area
export_db logo_gate.db
} message]} {puts "EXPLICIT_ROM_SYN_FAILED $message";exit 1}
puts "EXPLICIT_ROM_SYN_COMPLETE_NO_BIT"
exit
