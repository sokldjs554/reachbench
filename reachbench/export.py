"""Losslessly deduplicate camera recordings for the static demo. Run after evaluate."""
from pathlib import Path
import json,shutil

def main():
 root=Path('dist/data');s=json.loads((root/'summary.json').read_text());cameras=root/'cameras';cameras.mkdir(exist_ok=True)
 for row in s['episodes']:
  d=root/'frames'/row['id'];dest=cameras/f"{row['condition']}-{row['seed']}.png"
  if not dest.exists():shutil.copyfile(d/'camera.png',dest)
  if not d.exists():continue
  # One RGB input per scene; retain improved mid/end renders for the inspector.
  for file in d.glob('*.png'):
   if row['method']!='improved' or file.name not in ['middle.png','end.png']:file.unlink()
  if not list(d.iterdir()):d.rmdir()
 print('Exported',len(list(cameras.glob('*.png'))),'shared RGB inputs; no image re-encoding.')
if __name__=='__main__':main()
