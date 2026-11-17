"""Build vendored browser assets from pinned Python/npm packages. Run npm ci first."""
from pathlib import Path
import gzip,shutil,tempfile
import mujoco
from manipulation.build_model import build
root=Path(__file__).resolve().parents[1]
assert mujoco.__version__=='4.0.1','Native and WASM MuJoCo versions must match'
model=mujoco.MjModel.from_xml_path(str(build()))
out=root/'dist/assets';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as d:
    path=Path(d)/'workcell.mjb';mujoco.mj_saveModel(model,str(path))
    (out/'workcell.mjb.gz').write_bytes(gzip.compress(path.read_bytes(),mtime=0))
shutil.copy(root/'manipulation/assets/panda/LICENSE',out/'PANDA-LICENSE.txt')
vendor=root/'dist/vendor';vendor.mkdir(exist_ok=True)
for name in ['mujoco.js','mujoco.wasm']:
    shutil.copy(root/'node_modules/@mujoco/mujoco'/name,vendor/name)
for name in ['three.module.min.js','three.core.min.js']:
    shutil.copy(root/'node_modules/three/build'/name,vendor/name)
shutil.copy(root/'node_modules/three/examples/jsm/controls/OrbitControls.js',vendor/'OrbitControls.js')
shutil.copy(root/'node_modules/three/LICENSE',vendor/'THREE-LICENSE.txt')
print('Built MuJoCo 4.0.1 model and local browser dependencies')
