from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests'))
from style_fill_model import research
if __name__ == '__main__':
    print(research(Path(__file__).resolve().parents[1]/'docs/edge_style_fill_v1_evidence'))
