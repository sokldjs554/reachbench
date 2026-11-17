import os
os.environ.setdefault('MUJOCO_GL','egl')
from pathlib import Path
import numpy as np
import mujoco
from .build_model import ROOT,build

HOME=np.array([0,-.45,0,-2.05,0,1.6,.7854])
class Workcell:
    def __init__(self,seed=10,condition='normal',renderer=True):
        path=ROOT/'workcell.xml'
        if not path.exists():build()
        self.model=mujoco.MjModel.from_xml_path(str(path));self.data=mujoco.MjData(self.model)
        self.seed=seed;self.condition=condition;self.renderer=None;self.renderer_enabled=renderer
        self.tcp=self.model.site('tcp').id;self.cube=self.model.body('cube').id
        self.adr=self.model.jnt_qposadr[self.model.joint('cube_joint').id]
        self.data.qpos[:7]=HOME;self.data.qpos[7:9]=.04;self.data.ctrl[:7]=HOME;self.data.ctrl[7]=255
        state=int(seed)&0xffffffff
        def rand():
            nonlocal state
            state=(1664525*state+1013904223)&0xffffffff
            return state/4294967296
        for _ in range(8):rand()
        self.initial=np.array([.43+.08*rand(),-.05+.07*rand(),.383])
        if condition=='unreachable':self.initial[0]=.95
        self.data.qpos[self.adr:self.adr+3]=self.initial
        self.data.qpos[self.adr+3:self.adr+7]=[1,0,0,0]
        self.model.body_pos[self.model.body('occluder').id]=[.48,-.20,.47] if condition=='occluded' else [.48,-.20,-.5]
        mujoco.mj_forward(self.model,self.data)
        self.advance(.5)
        self.ikdata=mujoco.MjData(self.model)
        self.contacts=[]
    def __enter__(self):return self
    def __exit__(self,*a):self.close()
    def close(self):
        if self.renderer:self.renderer.close()
    def command(self,q,grip):
        self.data.ctrl[:7]=q;self.data.ctrl[7]=grip
    def advance(self,seconds):
        for _ in range(round(seconds/self.model.opt.timestep)):
            mujoco.mj_step(self.model,self.data)
    def truth(self):return self.data.xpos[self.cube].copy()
    def observe(self,camera='front',size=224):
        if self.renderer is None:self.renderer=mujoco.Renderer(self.model,height=size,width=size)
        self.renderer.update_scene(self.data,camera=camera)
        rgb=self.renderer.render().copy();self.renderer.enable_depth_rendering()
        depth=self.renderer.render().copy();self.renderer.disable_depth_rendering()
        cid=self.model.camera(camera).id
        return dict(rgb=rgb,depth=depth,rotation=self.data.cam_xmat[cid].reshape(3,3).copy(),position=self.data.cam_xpos[cid].copy(),fovy=float(self.model.cam_fovy[cid]))
    def ik(self,target,seed=None):
        d=self.ikdata;d.qpos[:]=self.data.qpos;d.qpos[:7]=self.data.qpos[:7] if seed is None else seed
        desired=np.diag([1,-1,-1]);jp=np.zeros((3,self.model.nv));jr=np.zeros_like(jp)
        for _ in range(150):
            mujoco.mj_forward(self.model,d)
            R=d.site_xmat[self.tcp].reshape(3,3)
            rot=.5*sum((np.cross(R[:,k],desired[:,k]) for k in range(3)))
            err=np.r_[np.asarray(target)-d.site_xpos[self.tcp],rot*.6]
            if np.linalg.norm(err)<.0005:break
            mujoco.mj_jacSite(self.model,d,jp,jr,self.tcp)
            J=np.vstack([jp[:,:7],jr[:,:7]*.6]);dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*.003,err)
            d.qpos[:7]+=np.clip(dq,-.08,.08)
            d.qpos[:7]=np.clip(d.qpos[:7],self.model.jnt_range[:7,0]+.02,self.model.jnt_range[:7,1]-.02)
        return d.qpos[:7].copy()
