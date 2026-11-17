"""Build a credential-free, portable source+data download, excluding this ZIP itself."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1];out=root/'work/reachbench-source.zip';out.parent.mkdir(exist_ok=True)
include=['README.md','LICENSE','requirements.txt','requirements-dev.txt','requirements-browser.txt','package.json','package-lock.json','.gitignore','reachbench','scripts','tests','docs','dist']
with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=6) as z:
 for item in include:
  p=root/item
  files=p.rglob('*') if p.is_dir() else [p]
  for f in files:
   if not f.is_file() or f==out or '__pycache__' in f.parts or 'local' in f.parts or any(x.startswith('local-') for x in f.parts):continue
   z.write(f,'reachbench/'+str(f.relative_to(root)))
print(out.name,out.stat().st_size,'bytes')
