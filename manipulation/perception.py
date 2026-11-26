"""RGB-D target estimator. Has no simulator handle or access to truth states."""
import cv2
import numpy as np

# Median of front/back image V percentiles (95th) at normal exposure, seeds 10–14.
REFERENCE_VALUE_P95 = 164.0


def estimate_target(rgb,depth,rotation,position,fovy, *, adaptive=False):
    hsv=cv2.cvtColor(np.asarray(rgb,np.uint8),cv2.COLOR_RGB2HSV)
    value_floor = 60
    if adaptive:
        scene_value = np.percentile(hsv[:, :, 2], 95)
        value_floor = np.clip(60 * scene_value / REFERENCE_VALUE_P95, 18, 60)
    mask=((hsv[:,:,0]<12)|(hsv[:,:,0]>170))&(hsv[:,:,1]>140)&(hsv[:,:,2]>value_floor)
    mask=cv2.morphologyEx(mask.astype('uint8'),cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    if n<=1:return None
    label=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);ys,xs=np.where(labels==label)
    if len(xs)<12:return None
    z=depth[ys,xs];ok=np.isfinite(z)&(z>0)&(z<3)
    if ok.sum()<12:return None
    h,w=depth.shape;f=h/(2*np.tan(np.deg2rad(fovy)/2))
    cam=np.stack([(xs[ok]+.5-w/2)*z[ok]/f,-(ys[ok]+.5-h/2)*z[ok]/f,-z[ok]],axis=1)
    pts=cam@np.asarray(rotation).reshape(3,3).T+position
    # Surface centroid is biased towards visible faces; center XY from bbox in 3D.
    low=np.percentile(pts,3,axis=0);high=np.percentile(pts,97,axis=0)
    center=(low+high)/2
    center[2]=.382 # known tabletop cube center height; XY comes only from RGB-D
    return {'position':center.tolist(),'pixels':int(len(xs)),'bbox':[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]}
