"""Repeat the read-only latency-path audit on this candidate's exact route."""
import audit_latency_cdc as audit
from build_inspection_parts_motion import OUT
audit.OUT=OUT
if __name__=='__main__':audit.main()
