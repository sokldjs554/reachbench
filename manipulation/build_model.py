"""Add our task to the licensed Panda model; export identical native/WASM model."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).parent/'assets'
def build():
    tree=ET.parse(ROOT/'panda/panda.xml');r=tree.getroot()
    r.set('model','ReachBench Panda recovery workcell')
    r.find('compiler').set('meshdir','panda/assets')
    r.find('option').set('timestep','0.002')
    r.find('option').set('gravity','0 0 -9.81')
    r.remove(r.find('keyframe'))
    vis=ET.SubElement(r,'visual');ET.SubElement(vis,'global',offwidth='800',offheight='600')
    ET.SubElement(vis,'quality',shadowsize='2048')
    a=r.find('asset');ET.SubElement(a,'texture',name='grid',type='2d',builtin='checker',rgb1='.25 .30 .34',rgb2='.28 .33 .37',width='512',height='512')
    ET.SubElement(a,'material',name='floor',texture='grid',texrepeat='8 8',reflectance='.05')
    w=r.find('worldbody');w.find("body[@name='link0']").set('pos','0 0 .36')
    ET.SubElement(w,'light',pos='0 -1 2.4',dir='0 .3 -1',diffuse='.8 .8 .8')
    ET.SubElement(w,'geom',name='ground',type='plane',size='3 3 .1',rgba='.2 .24 .29 1',material='floor')
    ET.SubElement(w,'geom',name='table',type='box',size='.48 .48 .025',pos='.35 0 .335',rgba='.55 .6 .64 1')
    ET.SubElement(w,'geom',name='tray_base',type='box',size='.085 .08 .006',pos='.48 .24 .366',rgba='.08 .40 .40 1')
    for name,size,pos in [('tray_l','.005 .085 .018','.39 .24 .382'),('tray_r','.005 .085 .018','.57 .24 .382'),('tray_back','.085 .005 .018','.48 .325 .382')]:
        ET.SubElement(w,'geom',name=name,type='box',size=size,pos=pos,rgba='.08 .40 .40 1')
    ob=ET.SubElement(w,'body',name='occluder',pos='.48 -.2 -.5')
    ET.SubElement(ob,'geom',name='occluder_geom',type='box',size='.15 .018 .11',rgba='.10 .20 .29 1')
    cube=ET.SubElement(w,'body',name='cube',pos='.48 -.025 .385')
    ET.SubElement(cube,'freejoint',name='cube_joint')
    ET.SubElement(cube,'geom',name='cube_geom',type='box',size='.022 .022 .022',mass='.065',friction='1.2 .02 .001',rgba='.9 .13 .08 1',condim='4')
    hand=r.find(".//body[@name='hand']")
    ET.SubElement(hand,'site',name='tcp',pos='0 0 .1034',size='.005',rgba='0 1 0 0')
    for name,pos,target in [('front',[.5,-1.0,1.05],[.48,0,.38]),('back',[.5,1.05,1.2],[.48,0,.38]),('observer',[1.25,-1.15,1.25],[.32,.02,.5])]:
        back=np.array(pos)-target;back/=np.linalg.norm(back)
        right=np.cross([0,0,1],back);right/=np.linalg.norm(right);up=np.cross(back,right)
        ET.SubElement(w,'camera',name=name,pos=' '.join(map(str,pos)),xyaxes=' '.join(map(str,np.r_[right,up])),fovy='45')
    for e in r.findall(".//default[@class='finger']/joint"):e.set('damping','2')
    path=ROOT/'workcell.xml';ET.indent(tree);tree.write(path)
    return path
if __name__=='__main__':
    import mujoco
    p=build();m=mujoco.MjModel.from_xml_path(str(p))
    out=Path('dist/assets');out.mkdir(parents=True,exist_ok=True)
    mujoco.mj_saveModel(m,str(out/'workcell.mjb'))
    print('model',m.nq,m.nv,m.ngeom,'bytes',(out/'workcell.mjb').stat().st_size)
