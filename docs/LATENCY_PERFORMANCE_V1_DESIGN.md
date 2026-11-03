# LATENCY_PERFORMANCE_V1 integration design (MAIN, in development)

Baseline: TRACK_REGION_FIX_V1, source publication072bc0f8, unmerged PR29.
LATENCY PR5 at87bb9a53 supplies the same-frame event semantics, not permission to
merge or overwrite teammate work. MAIN's adapters live under the production HDL
vision directory; no teammate feature files change. User explicitly requested
integration of challenge3 and extension4 while preserving other features.

## Measurement boundary and identity

The start is the first valid decoded RAW four-pixel beat before ISP, including
inline and early SOF. The end is the first real HDMI DE pixel at the transmitter
input. Exposure, sensor readout before this point and monitor latency are outside
this boundary. A common configured75MHz reference counts10us ticks; this is not a
frequency calibration. Registered Gray time passes two synchronization registers
to CSI, then is captured with a32-bit session and32-bit frame identity. Frame-ID
wrap increments the session; exhausting the identity space disables qualification.
Global reset clears every association/FIFO/slot and restarts the association
lifetime; identifiers are never compared across a global reset.

Each packed128-bit pixel word carries its87-bit observation tag in the SAME
official native FIFO word. Wider RAM words share the existing pointer/control
logic. There is no parallel FIFO alignment assumption, extra video word or video
backpressure. The vendor core source, burst arbitration and DDR addresses remain
unchanged. Default-disabled observation ports preserve standalone legacy clients.

The DDR journal accepts an exact172800-word, contiguous-address frame only when
its source geometry, final qualification and identity agree. Starting a write
invalidates the old slot generation. Completion is the ordered user-command FIFO
boundary, not ISP EOF: later accepted reads queue behind all writes. Actual native
FIFO/MC ordering must be integration-tested before release. A command loss, extra
word, bad address or missing frame invalidates the association.

The actual video_out read-selection edge snapshots identity/time/validity. This
held tuple crosses by a synchronized change toggle with an additional settling
cycle and must arrive before HDMI first DE. Missing, duplicate or late metadata
is invalid. It never fetches a slot's latest identity at output. Outstanding old
DDR responses at FIFO reset, read-slot overwrite, command loss or actual read-FIFO
underflow invalidate the frame. Results publish at the following VSYNC only after
all921600 pixels and trailing blanking; this defers statistics, not the measured
timestamp. Read-side tests must establish the actual blanking/CDC boundary.

Newly displayed identities update LAST/MIN/MAX and sample count. Repetitions
update AGE and REP status, never the new-image latency count. Errors are excluded,
not converted to plausible zeroes. Untouched records expire within one second;
the20-bit timebase wraps after10.48576 seconds. A reference-clock heartbeat watchdog
also clears records if that clock stops, preventing stale timestamp resurrection.
An invalid clock/reference or association cannot establish an end-to-end sample.

## Visualization

Transparent original-project font, panel x256..639/y16..79. Four16px text rows:

- LAT in decimal milliseconds with2 fractional digits and NEW/REP/BAD/WAIT.
- MIN and MAX of distinct, qualified first displays in the current reset lifetime.
- F: frame ID, N: accepted distinct sample count, E: invalid image count, all HEX.
- AGE in milliseconds, and10US indicating timestamp granularity.

LAT/MIN/MAX retain the last valid results during BAD; BAD is not a successful
measurement. AGE is the last qualified displayed image's age. The existing mixer
pipeline supplies the font's synchronous lookup stage, adding no RGB/DE cycles.
Existing Logo and status OSD keep priority; user buttons/switches are unchanged.

## Resource changes and evidence boundaries

One DP16 native RAM replaces the two row memories per four-hop stage, preserving
3clocks/hop. Native independently modelled tests pass168500 beats across full and
partial-word widths. Actual isolated synthesis confirms105→101 ERAM; its final
physical result is still pending when this document is first written.

Exact SP read-before-write rings were tested for RGB/gray/config payload delays.
Native random/reset checks pass, but each32-bit native SP maps to TWO ERAMs.
The integrated experiment needed112/108ERAM. This route was rejected. The formal
RGB/gray/binary payload delay implementation remains byte-identical to the baseline.

The selected alternative moves the existing Gaussian and NMS synchronous row
arrays from LUT RAM to native RAM, replacing704LUT-RAM cells. R0 used6ERAM and
passed final STA(+0.127ns setup/+0.020ns hold) plus18 full720p reference frames.
It did not generate a bit; its source and full build evidence are retained.

R1 retimes the row1 old-data access from G2/N2 to G1/N1. G2/N2 registers that old
row1 and reads-before-writing row2 at its matching column. Both histories now use
disjoint regions of the SAME DP16 bank: Gaussian1bank, NMS2banks. The original
G2/N2 windows, borders, metadata and4cycles/stage remain exact; widths above2048
retain the old generic arrays. Independent old software vectors(1282Gaussian/
2564NMS beats), reset cases and18 full720p stream frames pass with this retiming.

The23-bit config delay uses an exact unreset per-clock shift chain instead of
2ERAM. Four-hop coalescing frees4ERAM; wider pixel/tag FIFO costs2 and compact
font costs1. Net105-4-2+3+2+1=105ERAM, confirmed by the retimed synthesis. Final
Slice and timing still require R1 physical build; R0 timing is not reused as R1.

Actual constraint-derived clocks are CSI~59.995MHz, DDR user66.667MHz and HDMI
75MHz(nominal configured, not physically calibrated). DDR expiry33333333cycles
is one half-second window; heartbeat timeout66667cycles is1ms. A reference outage
after acquisition of its heartbeat latches invalid until global reset, so timing
across a stopped reference is never silently accepted after it resumes.

One resettable committed bit per slot protects unreset journal payload RAM; no
uninitialized metadata is eligible. Source identity/timestamp is held until the
next RAW frame. The DDR per-word identity check rejects a packed frame straddling
that change, avoiding redundant identity register banks. All actual algorithm/UI
pixels and31-cycle common stream latency must still pass full old-mode regression.

These are separate performance and measurement checkpoints. Neither an intended
RAM saving nor passing standalone tests proves the complete system fits or meets
timing. No candidate bit exists yet. Existing CDC Gray-pointer exception coverage
remains an independent risk; global PLL/SDC/pins are not relaxed. Newly introduced
Gray time/held-bus paths require protocol plus as-built route/CDC inspection.
