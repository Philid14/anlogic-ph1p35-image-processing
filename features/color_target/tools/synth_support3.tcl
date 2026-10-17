# Run from an output directory; use a forward-slash absolute script argument.
# COLOR_SUPPORT_TOP=support3_bypass_synth_top selects the default bypass harness.
set root [file normalize [file join [file dirname [info script]] ..]]
set top support3_synth_top
if {[info exists ::env(COLOR_SUPPORT_TOP)]} {set top $::env(COLOR_SUPPORT_TOP)}
if {[catch {
    import_device ph1_35p.db -package PH1P35MDG324 -speed 3
    analyze -file [file join $root rtl color_target_support3.v]
    if {[info exists ::env(COLOR_SUPPORT_TEST_HEIGHT)]} {
        analyze -file [file join $root tools support3_synth_top.v] -define "SUPPORT3_TEST_HEIGHT=$::env(COLOR_SUPPORT_TEST_HEIGHT)"
    } else {
        analyze -file [file join $root tools support3_synth_top.v]
    }
    elaborate -top $top
    set sdc [open support3_test.sdc w]
    puts $sdc {create_clock -name support3_test_clk -period 10.0 [get_ports clk]}
    close $sdc
    read_sdc support3_test.sdc
    optimize_rtl
    report_area -file support3_rtl.area
    optimize_gate -packarea support3_gate.area
    if {[llength [get_clocks support3_test_clk]] == 0} {error "Missing test clock"}
    report_area -file support3_gate.area
    report_timing_status -file support3_gate.ts
    write_verilog support3_gate.v -nobuf
    export_db support3_gate.db
} message]} {
    puts "FAIL_SUPPORT3_SYNTH $message"
    exit 1
}
puts "PASS_SUPPORT3_SYNTH top=$top"
exit
