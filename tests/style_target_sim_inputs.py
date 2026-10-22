"""Real local vendor simulation models and tracked ROM initializer setup."""
import os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'
HDL=PROJECT.parent/'user_source/hdl_source'

def prepare_logo_inputs(out,logo=None,vendor=None):
    logo=logo or HDL/'target/target_logo_palette.v'
    if 'PH1P_LOGIC_ERAM' not in logo.read_text():return [],[],[]
    data=[]
    for name in ('style_logo_index.dath','style_logo_palette.dath'):
        source=HDL/'target'/name
        if source.exists():shutil.copy2(source,out/name);data.append(source)
    model=vendor or Path(os.environ.get('TD_HOME','D:/TD'))/'sim_release/ph1p/ph1p_logic_eram.v'
    models=[model.resolve(),model.resolve().with_name('ph1p_phy_gsr.v')]
    assert all(p.is_file() for p in models),'Official TD PH1P simulation models are required'
    return models,data,['PH1P_PHY_GSR']

def manifest_name(p):
    try:return p.relative_to(ROOT).as_posix()
    except ValueError:return p.as_posix()
