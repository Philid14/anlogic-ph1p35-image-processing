"""Materialize independent baseline vectors on a fresh checkout, never need old tmp."""
from vision_sim import ROOT
def baseline():
 folder=ROOT/'tmp/ruler_cm/stream_r1';stim,pack=folder/'stim.txt',folder/'pack.txt'
 if not stim.exists() or not pack.exists():
  import ruler_cm_stream_vectors as model
  folder.mkdir(parents=True,exist_ok=True);model.vectors(folder,1280,720,True)
 return stim,pack
