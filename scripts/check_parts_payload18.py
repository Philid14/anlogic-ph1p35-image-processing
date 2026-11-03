"""Isolated resource experiment: legal native18bit RAM words, no promotion.

Never touches formal RTL/.al or the active route. Reduces physical width
fragmentation of the previously rejected32bit-per-word delay experiment.
"""
import os,json
from pathlib import Path
import check_latency_staging_resources as resource

ROOT=resource.ROOT
STAGE=ROOT/'tmp/inspection_parts_motion/payload18_staging_r1'
OUT=ROOT/'tmp/inspection_parts_motion/resource_payload18_r1'

def main():
 assert not STAGE.exists() and not OUT.exists()
 (STAGE/'isp').mkdir(parents=True);(STAGE/'vision').mkdir()
 current=(resource.HDL/'isp/edge_control_stream.v').read_text()
 prior=(ROOT/'tmp/inspection_parts_motion/staging/isp/edge_control_stream.v').read_text()
 # Only the independently tested payload-delay region is transplanted;
 # profile/view/adapters remain the exact current R2 implementation.
 start=current.index('    reg [95:0] original_p ')
 end=current.index('    always @(posedge clk or negedge rst_n)',start)
 pstart=prior.index('    reg [95:0] original_p ')
 pend=prior.index('    always @(posedge clk or negedge rst_n)',pstart)
 (STAGE/'isp/edge_control_stream.v').write_text(current[:start]+prior[pstart:pend]+current[end:])
 helper=(resource.HDL/'vision/inspection_payload_delay.v').read_text()
 helper=helper.replace('(WIDTH+31)/32','(WIDTH+17)/18').replace('[31:0]','[17:0]').replace('b<32','b<18').replace('s*32+b','s*18+b')
 helper=helper.replace('DATA_WIDTH_A(32)','DATA_WIDTH_A(18)').replace('DATA_WIDTH_B(32)','DATA_WIDTH_B(18)')
 helper=helper.replace('ADDR_WIDTH_A(9)','ADDR_WIDTH_A(10)').replace('ADDR_WIDTH_B(9)','ADDR_WIDTH_B(10)')
 helper=helper.replace('DATA_DEPTH_A(512)','DATA_DEPTH_A(1024)').replace('DATA_DEPTH_B(512)','DATA_DEPTH_B(1024)')
 helper=helper.replace('(9-AW)','(10-AW)').replace("addrb(9'd0)","addrb(10'd0)").replace("dib(32'd0)","dib(18'd0)")
 (STAGE/'vision/inspection_payload_delay.v').write_text(helper)
 # The generic ADDED loop only admits formal paths. Inline this experimental
 # helper into the frozen adapter instead, so the TD manifest proves which
 # geometry is ACTUALLY compiled. Do not silently use the formal32bit helper.
 adapter=STAGE/'isp/edge_control_stream.v'
 adapter.write_text(adapter.read_text()+'\n'+helper)
 resource.STAGING=STAGE;resource.OUT=OUT
 resource.main()
 print('Resource-only; no candidate, no formal files changed')

if __name__=='__main__':main()
