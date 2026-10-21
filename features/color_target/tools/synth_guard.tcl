# Standalone gate experiment only: NO physical design, MAIN edits or bit.
set root [file normalize [file join [file dirname [info script]] ..]]
set tw $::env(COLOR_GUARD_TIME_W)
set enabled $::env(COLOR_GUARD_ENABLED)
if {$tw ni {32 64} || $enabled ni {0 1}} {error "Unsupported measurement profile"}
if {[catch {
    import_device ph1_35p.db -package PH1P35MDG324 -speed 3
    foreach src {color_target_track.v color_target_track_guard.v} {
        analyze -file [file join $root rtl $src]
    }
    analyze -file [file join $root tools guard_synth_top.v] -define "GUARD_SYNTH_TIME_W=$tw GUARD_SYNTH_ENABLED=$enabled"
    elaborate -top guard_synth_top
    set sdc [open guard_test.sdc w]
    puts $sdc {create_clock -name guard_test_clk -period 10.0 [get_ports clk]}
    close $sdc
    read_sdc guard_test.sdc
    optimize_rtl
    report_area -file guard_rtl.area
    optimize_gate -packarea guard_gate.area
    if {[llength [get_clocks guard_test_clk]] != 1} {error "Missing measurement clock"}
    report_area -file guard_gate.area
    report_timing_status -file guard_gate.ts
    report_timing_summary -file guard_summary.txt
    # Summary includes actual critical paths; an unnamed report_timing_path
    # returns no paths in TD V6.2 and must not be mistaken for timing coverage.
    export_db guard_gate.db
} message]} {
    puts "FAIL_GUARD_SYNTH $message"
    exit 1
}
puts "GUARD_SYNTH_COMPLETE time_w=$tw enabled=$enabled"
exit
