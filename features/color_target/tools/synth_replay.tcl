# Standalone resource check, no physical design or bit generation.
set root [file normalize [file join [file dirname [info script]] ..]]
set enable 0
if {[info exists ::env(COLOR_REPLAY_FILTER_ENABLE)]} {set enable $::env(COLOR_REPLAY_FILTER_ENABLE)}
if {$enable != 0 && $enable != 1} {error "COLOR_REPLAY_FILTER_ENABLE must be 0 or 1"}
if {[catch {
    import_device ph1_35p.db -package PH1P35MDG324 -speed 3
    foreach src {color_classify.v color_target_support3.v color_target_mask_stats.v color_target_detect_stream.v} {
        analyze -file [file join $root rtl $src]
    }
    analyze -file [file join $root tools replay_synth_top.v] -define "REPLAY_FILTER_ENABLE=$enable"
    elaborate -top replay_synth_top
    set sdc [open replay_test.sdc w]
    puts $sdc {create_clock -name replay_test_clk -period 10.0 [get_ports clk]}
    close $sdc
    read_sdc replay_test.sdc
    optimize_rtl
    optimize_gate -packarea replay_gate.area
    if {[llength [get_clocks replay_test_clk]] == 0} {error "Missing test clock"}
    report_area -file replay_gate.area
    report_timing_status -file replay_gate.ts
    report_timing_summary -file replay_summary.txt
} message]} {
    puts "FAIL_REPLAY_SYNTH $message"
    exit 1
}
puts "PASS_REPLAY_SYNTH filter=$enable"
exit
