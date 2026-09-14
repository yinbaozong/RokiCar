"""Deterministic CPU z-buffer preview of the exported binary STL geometry."""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image

P=Path(__file__).resolve().parents[1]; W=P/'build'; OUT=P.parent/'04_media';OUT.mkdir(exist_ok=True)
scene=json.loads((W/'scene.json').read_text(encoding='utf-8'))
def norm(v):return v/np.linalg.norm(v)
parts=[]
for obj in scene['objects']:
 # Internal electronics are hidden by the opaque shell in all these views.
 if obj['name'].startswith('Original component') and int(obj['name'].split()[-1]) not in [0,1,2,3,14]:continue
 path=P/obj['path']
 with path.open('rb') as f:
  f.seek(80);n=int.from_bytes(f.read(4),'little')
  data=np.frombuffer(f.read(),dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]),count=n)
  verts=data['v'].astype(float)
 name=obj['name']
 if name=='02_hatch': verts[:,:,2]+=100
 elif name=='01_shell' or name=='Original component 14': verts[:,:,2]+=45
 elif name=='Original component 0': verts[:,:,2]-=25
 else:
  center=verts.mean(axis=(0,1));r=np.linalg.norm(center[:2]);verts[:,:,:2]+=center[:2]/r*23
 parts.append((verts,np.array(obj['color'])))

def render(name,pos,up):
 print('Rendering',name,flush=True)
 verts=np.concatenate([p[0] for p in parts]); cols=np.concatenate([np.tile(p[1],(len(p[0]),1)) for p in parts])
 center=np.array([0,8,13]); eye=norm(np.array(pos)-center); right=norm(np.cross(np.array(up),eye)); top=np.cross(eye,right)
 projected=np.stack([(verts-center)@right,(verts-center)@top,(verts-center)@eye],axis=-1)
 width,height=1800,1500
 mi=projected[:,:,:2].min(axis=(0,1));ma=projected[:,:,:2].max(axis=(0,1))
 scale=min((width-200)/(ma[0]-mi[0]),(height-180)/(ma[1]-mi[1]));mid=(mi+ma)/2
 xy=projected[:,:,:2];xy[:,:,0]=(xy[:,:,0]-mid[0])*scale+width/2;xy[:,:,1]=height/2-(xy[:,:,1]-mid[1])*scale
 fn=np.cross(verts[:,1]-verts[:,0],verts[:,2]-verts[:,0]);length=np.linalg.norm(fn,axis=1)
 fn/=np.maximum(length[:,None],1e-20)
 light=norm(np.array([-1,-2,4]));fill=norm(np.array([2,1,2]));shade=.53+.46*np.maximum(0,fn@light)+.18*np.maximum(0,fn@fill)
 color=np.clip(cols*shade[:,None],0,1)*255
 yy=np.linspace(0,1,height)[:,None,None];frame=np.broadcast_to(249-yy*10,(height,width,3)).copy().astype(np.uint8)
 depth=np.full((height,width),-1e10,dtype=np.float32)
 # Rasterizing far to near reduces the cost of pixels rejected by the z-buffer.
 order=np.argsort(projected[:,:,2].mean(axis=1))
 for i in order:
  t=projected[i];x0,y0=t[0,:2];x1,y1=t[1,:2];x2,y2=t[2,:2]
  den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
  if abs(den)<1e-7:continue
  lo=np.maximum(np.floor(t[:,:2].min(axis=0)).astype(int),[0,0]);hi=np.minimum(np.ceil(t[:,:2].max(axis=0)).astype(int),[width-1,height-1])
  if np.any(lo>hi):continue
  xx=np.arange(lo[0],hi[0]+1)[None,:]+.5;yy=np.arange(lo[1],hi[1]+1)[:,None]+.5
  a=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den;b=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den;c=1-a-b
  zz=a*t[0,2]+b*t[1,2]+c*t[2,2]
  d=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
  mask=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(zz>d)
  d[mask]=zz[mask];frame[lo[1]:hi[1]+1,lo[0]:hi[0]+1][mask]=color[i].astype(np.uint8)
 # Light screen-space contact shading, based only on rendered geometry depth.
 occupied=depth>-1e9;occ=np.zeros_like(depth)
 for dx,dy in [(3,0),(-3,0),(0,3),(0,-3),(8,0),(-8,0),(0,8),(0,-8)]:
  other=np.roll(depth,(dy,dx),(0,1));diff=other-depth
  occ+=(diff>.25)&(diff<3)&occupied
 frame=(frame.astype(float)*(1-occ[:,:,None]*.018)).clip(0,255).astype(np.uint8)
 image=Image.fromarray(frame).resize((1440,1200),Image.Resampling.LANCZOS)
 image.save(OUT/name)

render('04_exploded_cad.png',[175,-270,160],[0,0,1])
print('V5 PREVIEW COMPLETE',flush=True)
