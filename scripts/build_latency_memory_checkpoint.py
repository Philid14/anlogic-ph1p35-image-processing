"""Isolated, committed-source SYN checkpoint; never produces a candidate bit."""
import json
import build_track_region_fix as build

build.OUT=build.ROOT/'tmp/latency_performance/memory_syn_r0'
build.BASE='072bc0f8858ceb3009659f8df7cb02b9da05ed36'
build.CHANGED={build.HDL+'isp/edge_link_pair_3x3.v'}

if __name__=='__main__':
    # Snapshot checks still cover all original TD inputs, teammate provenance,
    # unchanged synthesis/physical settings and every historical bit hash.
    build.main()
