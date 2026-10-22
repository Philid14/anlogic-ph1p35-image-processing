if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/route.db}
commit_param -step bitgen
bitgen -bit {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/camera_to_dsi_display.bit}
export_bitgen_param -file {D:/anlogic_formal_project/tmp/style_v2_target_v1/route_explicit_logo_20/bitgen_params.txt}
} message]} {puts "BITGEN_FAILED $message"; exit 1}
puts "VERIFIED_ROUTE_BITGEN_COMPLETE"
exit
