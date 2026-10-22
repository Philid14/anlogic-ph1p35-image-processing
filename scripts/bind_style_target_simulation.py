"""Bind exact simulation input hashes to a commit, allowing only newline changes."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--commit',required=True)
    ap.add_argument('--allow-toolchain',action='store_true');a=ap.parse_args()
    folder=a.directory.resolve();manifest=json.loads((folder/'SOURCE_MANIFEST.json').read_text());mapped={};mixed={};external={}
    commit=subprocess.check_output(['git','rev-parse',a.commit],cwd=ROOT).decode().strip()
    for rel,sha in manifest.items():
        p=Path(rel)
        if p.is_absolute() and not p.is_relative_to(ROOT):
            assert a.allow_toolchain and p.name in ('ph1p_logic_eram.v','ph1p_phy_gsr.v')
            assert p.parent.as_posix().endswith('/sim_release/ph1p')
            assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
            external[rel]=sha;continue
        blob=subprocess.check_output(['git','show',commit+':'+rel],cwd=ROOT);lf=blob.replace(b'\r\n',b'\n')
        for mode,raw in [('git_blob',blob),('LF',lf),('CRLF',lf.replace(b'\n',b'\r\n'))]:
            if hashlib.sha256(raw).hexdigest()==sha:mapped[rel]=mode;break
        if rel not in mapped:
            raw=(ROOT/rel).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==sha and raw.replace(b'\r\n',b'\n')==lf,rel
            mapped[rel]='manifest-matching mixed newlines; normalized content equals Git';mixed[rel]=raw
    if mixed:
        with zipfile.ZipFile(folder/'EXACT_MIXED_NEWLINE_INPUTS.zip','w',zipfile.ZIP_DEFLATED) as z:
            for rel,raw in mixed.items():z.writestr(rel,raw)
    (folder/'COMMIT_BINDING.json').write_text(json.dumps(dict(source_commit=commit,
        all_input_content_matches_commit=not bool(external),all_project_input_content_matches_commit=True,
        external_toolchain_inputs=external,newline_representations=mapped),indent=2)+'\n')
    print('Bound',len(mapped),'project inputs to',commit,'and',len(external),'hash-checked official toolchain dependencies')
if __name__=='__main__':main()
