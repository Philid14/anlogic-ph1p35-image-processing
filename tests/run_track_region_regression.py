"""Rerun the prior candidate's native tests without overwriting its evidence."""
import importlib,sys
from vision_sim import ROOT
CASES={c:'run_inspection_'+c for c in ('font','shape','drawing','track','config','reset','select','contract','legacy','integrated','track_stream')}
CASES['background_full']='run_measure_background_full'
def main():
 for case in sys.argv[1:]:
  module=importlib.import_module(CASES[case]);module.OUT=ROOT/'tmp/track_region_fix'/case
  module.main()
if __name__=='__main__':main()
