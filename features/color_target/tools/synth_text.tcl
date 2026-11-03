# Standalone gate synthesis of the text module. Run TD from an empty output
# directory. This does not edit the main TD project, place/route, or emit a bit.
# A synthetic 10 ns clock exercises synthesis; it is not a board timing claim.
# COLOR_TARGET_RTL may select an older RTL file for an equivalent comparison.
set rtl [file normalize [file join [file dirname [info script]] .. rtl color_target_text_overlay.v]]
if {[info exists ::env(COLOR_TARGET_RTL)]} {
    set rtl [file normalize $::env(COLOR_TARGET_RTL)]
}
if {[catch {
    import_device ph1_35p.db -package PH1P35MDG324 -speed 3
    analyze -file $rtl
    elaborate -top color_target_text_overlay
    set sdc [open text_test.sdc w]
    puts $sdc {create_clock -name text_test_clk -period 10.0 [get_ports clk]}
    close $sdc
    read_sdc text_test.sdc
    optimize_rtl
    report_area -file text_rtl.area
    optimize_gate -packarea text_gate.area
    if {[llength [get_clocks text_test_clk]] == 0} {
        error "The standalone test clock was not created"
    }
    report_area -file text_gate.area
    report_timing_status -file text_gate.ts
    export_db text_gate.db
} message]} {
    puts "FAIL_TEXT_SYNTH $message"
    exit 1
}
puts "PASS_TEXT_SYNTH source=$rtl"
exit
