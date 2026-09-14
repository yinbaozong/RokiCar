from pathlib import Path
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1]
fig,ax=plt.subplots(figsize=(10,5))
for n,col,label in [('01_shell','#219653','Fixed shell'),('02_hatch','#164a32','Removable lid')]:
 m=trimesh.load(P/'build'/'meshes'/(n+'.stl'),force='mesh')
 sec=m.section(plane_origin=[0,10,0],plane_normal=[0,1,0])
 for i,pts in enumerate(e.discrete(sec.vertices) for e in sec.entities):
  ax.plot(pts[:,0],pts[:,2],color=col,lw=2,label=label if i==0 else None)
ax.fill([30.5,40.5,40.5,30.5],[34.8,34.8,36,36],color='#edb23a',alpha=.35,label='Nail clearance envelope')
ax.annotate('Insert nail, then lift LID',xy=(31.1,36.35),xytext=(35,39),arrowprops=dict(arrowstyle='->'),fontsize=11)
ax.annotate('',xy=(32,35.4),xytext=(40,35.4),arrowprops=dict(arrowstyle='->',color='#bd7200',lw=2))
ax.set(xlim=(28,42),ylim=(32.5,40),xlabel='X (mm)',ylabel='Z (mm)',title='V7 actual mesh section at Y = 10 mm / opening width 8 mm')
ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='lower right',fontsize=9)
fig.tight_layout();fig.savefig(P/'images'/'02_grip_section.png',dpi=160)
print('SECTION COMPLETE')
