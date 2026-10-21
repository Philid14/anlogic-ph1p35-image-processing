# Placement-only diagnostic of the immutable synthesized gate DB. Never bitgen.
if {[catch {
    source ./settings.cfg
    import_device ph1_35p.db -package PH1P35MDG324 -speed 3
    open_project camera_to_dsi_display.prj -noanalyze
    import_db ../syn_1/camera_to_dsi_display_gate.db
    commit_param -step place
    place
    report_area -io_info -file D:/anlogic_formal_project/tmp/style_v2_target_v1/place_preflight_03.area
    export_db D:/anlogic_formal_project/tmp/style_v2_target_v1/place_preflight_03.db
} message]} {
    puts "PLACEMENT_PREFLIGHT_FAILED $message"
    exit 1
}
puts "PLACEMENT_PREFLIGHT_COMPLETE_NO_ROUTE_NO_BIT"
exit
