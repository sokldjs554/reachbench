"""ReachBench: CPU RGB perception -> joint planning -> kinematic collision evaluation.
No ground-truth object coordinates enter perceive() or plan(). Units: m, rad, s.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import heapq, math, time
import cv2
import numpy as np
import pybullet as p

BASE=np.array([-.5,0.]); LENGTHS=(.55,.45); WIDTH=.025
QSTART=np.array([-1.1,1.5]); LIMIT=2.7
W=320; CAMERA_Z=2.6; FOV=47.; F=W/(2*np.tan(np.deg2rad(FOV)/2))
TARGET_Z=.022; OBSTACLE_Z=.36

def fk(q):
    a=BASE+LENGTHS[0]*np.array([np.cos(q[0]),np.sin(q[0])])
    b=a+LENGTHS[1]*np.array([np.cos(sum(q)),np.sin(sum(q))])
    return np.array([BASE,a,b])

def ik(xy):
    x,y=np.array(xy)-BASE
    c=(x*x+y*y-sum(l*l for l in LENGTHS))/(2*np.prod(LENGTHS))
    if abs(c)>1:return []
    out=[]
    for s in [1,-1]:
        b=s*np.arccos(c);a=np.arctan2(y,x)-np.arctan2(LENGTHS[1]*np.sin(b),LENGTHS[0]+LENGTHS[1]*np.cos(b))
        q=np.array([a,b])
        if np.all(np.abs(q)<=LIMIT):out.append(q)
    return sorted(out,key=lambda q:np.linalg.norm(q-QSTART))

def segment_distance(point,a,b):
    t=np.clip(np.dot(point-a,b-a)/max(np.dot(b-a,b-a),1e-12),0,1)
    return np.linalg.norm(point-(a+t*(b-a)))

def clearance(q,obstacles):
    pts=fk(q)
    return min((segment_distance(np.array(o[:2]),a,b)-o[2]-WIDTH for o in obstacles for a,b in zip(pts[:-1],pts[1:])),default=1.)

def edge(a,b,obs,margin=0):
    steps=max(2,int(np.max(np.abs(b-a))/.025)+1)
    return all(clearance(a+(b-a)*t,obs)>margin for t in np.linspace(0,1,steps))

def plan(target,obstacles,method):
    goals=ik(target)
    if not goals:return None,'unreachable'
    if method=='direct':return [QSTART,goals[0]],'direct_joint'
    # A* over joint configuration space; goal joins are checked continuously.
    n=65; vals=np.linspace(-LIMIT,LIMIT,n); step=vals[1]-vals[0]
    def snap(q):return tuple(np.clip(np.rint((q+LIMIT)/step),0,n-1).astype(int))
    def coord(k):return np.array([vals[k[0]],vals[k[1]]])
    start=snap(QSTART); valid={}
    def free(k):
        if k not in valid:valid[k]=clearance(coord(k),obstacles)>.012
        return valid[k]
    if not edge(QSTART,coord(start),obstacles,.012):return None,'start_blocked'
    goal_nodes={snap(g):g for g in goals if clearance(g,obstacles)>.012 and edge(coord(snap(g)),g,obstacles,.012)}
    if not goal_nodes:return None,'goal_blocked'
    def h(k):return min(np.linalg.norm(coord(k)-g) for g in goal_nodes.values())
    queue=[(h(start),0.,start)]; costs={start:0.}; prev={}; final=None
    while queue:
        _,cost,k=heapq.heappop(queue)
        if cost>costs[k]+1e-10:continue
        if k in goal_nodes:final=k;break
        for dx,dy in [(a,b) for a in [-1,0,1] for b in [-1,0,1] if a or b]:
            nk=(k[0]+dx,k[1]+dy)
            if not all(0<=v<n for v in nk) or not free(nk):continue
            new=cost+step*np.hypot(dx,dy)
            if new>=costs.get(nk,float('inf')):continue
            if not edge(coord(k),coord(nk),obstacles,.012):continue
            costs[nk]=new;prev[nk]=k;heapq.heappush(queue,(new+h(nk),new,nk))
    if final is None:return None,'no_path'
    keys=[final]
    while keys[-1]!=start:keys.append(prev[keys[-1]])
    path=[QSTART]+[coord(k) for k in keys[::-1]]+[goal_nodes[final]]
    # Greedy shortcut preserves the same swept-edge collision test.
    short=[path[0]];i=0
    while i<len(path)-1:
        j=len(path)-1
        while j>i+1 and not edge(path[i],path[j],obstacles,.012):j-=1
        short.append(path[j]);i=j
    return short,'astar'

@dataclass
class Scene:
    seed:int
    condition:str
    target:list
    obstacles:list
    brightness:float=1.
    noise:float=0.
    occlude:bool=False
    calibration_dx:float=0.

def scene(seed,condition='nominal'):
    rng=np.random.default_rng(seed)
    target=[float(rng.uniform(.10,.32)),float(rng.uniform(.22,.46))]
    obs=[[float(rng.uniform(.20,.35)),float(rng.uniform(-.06,.12)),float(rng.uniform(.045,.075))]]
    s=Scene(seed,condition,target,obs)
    if condition=='dim':s.brightness=.38;s.noise=5.
    if condition=='clutter':s.obstacles.append([-.22,.34,.07])
    if condition=='occluded':s.occlude=True
    if condition=='calibration':s.calibration_dx=.065
    return s

class World:
    def __init__(self,s):
        self.s=s;self.cid=p.connect(p.DIRECT)
        p.setGravity(0,0,-9.81,physicsClientId=self.cid)
        def box(half,pos,color):
            v=p.createVisualShape(p.GEOM_BOX,halfExtents=half,rgbaColor=color,physicsClientId=self.cid)
            c=p.createCollisionShape(p.GEOM_BOX,halfExtents=half,physicsClientId=self.cid)
            return p.createMultiBody(0,c,v,pos,physicsClientId=self.cid)
        box([1.2,1.2,.02],[0,0,-.03],[.72,.74,.73,1])
        self.obs_ids=[]
        for x,y,r in s.obstacles:
            v=p.createVisualShape(p.GEOM_CYLINDER,radius=r,length=OBSTACLE_Z,rgbaColor=[.12,.38,.85,1],physicsClientId=self.cid)
            c=p.createCollisionShape(p.GEOM_CYLINDER,radius=r,height=OBSTACLE_Z,physicsClientId=self.cid)
            self.obs_ids.append(p.createMultiBody(0,c,v,[x,y,OBSTACLE_Z/2],physicsClientId=self.cid))
        v=p.createVisualShape(p.GEOM_CYLINDER,radius=.035,length=TARGET_Z,rgbaColor=[.95,.12,.08,1],physicsClientId=self.cid)
        p.createMultiBody(0,-1,v,[*s.target,TARGET_Z/2],physicsClientId=self.cid)
        visuals=[];collisions=[]
        for l in LENGTHS:
            visuals.append(p.createVisualShape(p.GEOM_BOX,halfExtents=[l/2,WIDTH,.025],visualFramePosition=[l/2,0,0],rgbaColor=[.83,.85,.82,1],physicsClientId=self.cid))
            collisions.append(p.createCollisionShape(p.GEOM_BOX,halfExtents=[l/2,WIDTH,.025],collisionFramePosition=[l/2,0,0],physicsClientId=self.cid))
        bv=p.createVisualShape(p.GEOM_CYLINDER,radius=.07,length=.19,rgbaColor=[.2,.23,.24,1],physicsClientId=self.cid)
        self.robot=p.createMultiBody(baseMass=0,baseVisualShapeIndex=bv,basePosition=[*BASE,.16],linkMasses=[1,1],linkCollisionShapeIndices=collisions,linkVisualShapeIndices=visuals,linkPositions=[[0,0,0],[LENGTHS[0],0,0]],linkOrientations=[[0,0,0,1]]*2,linkInertialFramePositions=[[0,0,0]]*2,linkInertialFrameOrientations=[[0,0,0,1]]*2,linkParentIndices=[0,1],linkJointTypes=[p.JOINT_REVOLUTE]*2,linkJointAxis=[[0,0,1]]*2,physicsClientId=self.cid)
        self.setq(QSTART)
    def setq(self,q):
        for j,v in enumerate(q):p.resetJointState(self.robot,j,float(v),physicsClientId=self.cid)
        p.performCollisionDetection(physicsClientId=self.cid)
    def collision(self):
        return any(p.getClosestPoints(self.robot,o,0,physicsClientId=self.cid) for o in self.obs_ids)
    def image(self,q=None):
        if q is not None:self.setq(q)
        view=p.computeViewMatrix([0,0,CAMERA_Z],[0,0,0],[0,1,0])
        proj=p.computeProjectionMatrixFOV(FOV,1,.1,5.)
        raw=p.getCameraImage(W,W,view,proj,renderer=p.ER_TINY_RENDERER,shadow=0,lightDirection=[0,0,1],physicsClientId=self.cid)
        rgb=np.array(raw[2],dtype=np.uint8).reshape(W,W,4)[:,:,:3].copy()
        rng=np.random.default_rng(self.s.seed+100000)
        rgb=np.clip(rgb.astype(float)*self.s.brightness+rng.normal(0,self.s.noise,rgb.shape),0,255).astype(np.uint8)
        if self.s.occlude:
            u,v=world_to_pixel(self.s.target,TARGET_Z)
            cv2.rectangle(rgb,(int(u)-12,int(v)-12),(int(u)+12,int(v)+12),(92,96,94),-1)
        return rgb
    def close(self):p.disconnect(self.cid)

def world_to_pixel(xy,z=0):return [W/2+F*xy[0]/(CAMERA_Z-z),W/2-F*xy[1]/(CAMERA_Z-z)]
def pixel_to_world(u,v,z=0,dx=0):return [(u-W/2)*(CAMERA_Z-z)/F+dx,(W/2-v)*(CAMERA_Z-z)/F]

def perceive(rgb,method,calibration_dx=0):
    # Only pixels and supplied calibration enter here. No Bullet segmentation IDs/depth/GT.
    if method=='rgb':
        r,g,b=cv2.split(rgb);target=((r>150)&(g<105)&(b<105)).astype('uint8')*255
        obstacle=((b>125)&(r<100)&(g<155)).astype('uint8')*255
    else:
        hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
        target=cv2.bitwise_or(cv2.inRange(hsv,(0,110,30),(12,255,255)),cv2.inRange(hsv,(170,110,30),(179,255,255)))
        obstacle=cv2.inRange(hsv,(95,100,25),(125,255,255))
        kernel=np.ones((3,3),np.uint8)
        target=cv2.morphologyEx(target,cv2.MORPH_OPEN,kernel)
        obstacle=cv2.morphologyEx(obstacle,cv2.MORPH_OPEN,kernel)
    def components(mask,z):
        cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        out=[]
        for c in cnts:
            area=cv2.contourArea(c)
            if area<7:continue
            (u,v),radius=cv2.minEnclosingCircle(c)
            xy=pixel_to_world(u,v,z,calibration_dx)
            out.append({'xy':xy,'radius':float(radius*(CAMERA_Z-z)/F),'pixel':[float(u),float(v)],'area':float(area)})
        return sorted(out,key=lambda x:-x['area'])
    ts=components(target,TARGET_Z);obs=components(obstacle,OBSTACLE_Z)
    return {'target':ts[0] if ts else None,'obstacles':obs,'target_pixels':int(np.count_nonzero(target))}

METHODS={'baseline':('rgb','direct'),'perception':('hsv','direct'),'planning':('rgb','astar'),'improved':('hsv','astar')}

def rollout(s,method,save_dir=None):
    world=World(s);rgb=world.image();pm,cm=METHODS[method]
    t=time.perf_counter();det=perceive(rgb,pm,s.calibration_dx);perception_ms=(time.perf_counter()-t)*1000
    path=None;plan_ms=0.;reason='target_missing'
    if det['target']:
        obs=[[*x['xy'],x['radius']] for x in det['obstacles']]
        t=time.perf_counter();path,reason=plan(det['target']['xy'],obs,cm);plan_ms=(time.perf_counter()-t)*1000
    qs=[QSTART.copy()]
    if path is not None:
        for a,b in zip(path[:-1],path[1:]):
            n=max(1,int(np.ceil(np.max(np.abs(b-a))/.025)))
            qs.extend(a+(b-a)*k/n for k in range(1,n+1))
    trace=[];hit=False;length=0.;last=fk(QSTART)[-1]
    for i,q in enumerate(qs):
        world.setq(q);tip=fk(q)[-1];length+=np.linalg.norm(tip-last);last=tip
        hit=world.collision()
        trace.append({'t':round(i*.05,3),'q':q.tolist(),'joints':fk(q).tolist(),'collision':bool(hit)})
        if hit:reason='collision';break
    error=float(np.linalg.norm(fk(qs[len(trace)-1])[-1]-s.target))
    success=bool(path is not None and not hit and error<=.035)
    if success:reason='reached'
    elif path is not None and not hit:reason='position_error'
    out={'seed':s.seed,'condition':s.condition,'method':method,'success':success,'reason':reason,'endpoint_error_mm':error*1000,'perception_error_mm':float(np.linalg.norm(np.array(det['target']['xy'])-s.target)*1000) if det['target'] else None,'perception_ms':perception_ms,'planning_ms':plan_ms,'duration_s':trace[-1]['t'],'path_length_m':float(length),'frames':len(trace),'detected':det,'scene':asdict(s),'trace':trace}
    if save_dir:
        d=Path(save_dir);d.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(d/'camera.png'),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        for name,idx in [('start',0),('middle',len(trace)//2),('end',len(trace)-1)]:
            img=world.image(trace[idx]['q']);cv2.imwrite(str(d/f'{name}.png'),cv2.cvtColor(img,cv2.COLOR_RGB2BGR))
    world.close();return out
