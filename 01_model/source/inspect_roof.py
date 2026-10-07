from pathlib import Path
import cadquery as cq
print('CadQuery loaded',flush=True)
s=cq.importers.importStep(str(Path(__file__).resolve().parents[1]/'reference'/'original_shell.step')).val()
f=max([f for f in s.Faces() if f.geomType()=='PLANE' and abs(f.Center().z-35)<1e-6],key=lambda f:f.Area())
print('roof area',f.Area(),'outer vertices',[(tuple(round(v,4) for v in p.Center().toTuple())) for p in f.outerWire().Vertices()],flush=True)
for w in f.innerWires():print('inner',[(tuple(round(v,4) for v in p.Center().toTuple())) for p in w.Vertices()],flush=True)
