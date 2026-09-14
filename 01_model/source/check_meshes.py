"""Check only the released print meshes; no new tests of unrelated project code."""
from pathlib import Path
import json
import trimesh
P=Path(__file__).resolve().parents[1]
rows=[]
for path in sorted((P/'print').glob('*.stl')):
 m=trimesh.load_mesh(path)
 row={'file':path.name,'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'bodies':int(m.body_count),'volume_mm3':float(m.volume),'triangles':len(m.faces),'bounds':m.bounds.tolist()}
 rows.append(row)
 assert m.is_watertight and m.is_winding_consistent and m.volume>0,path.name
 assert m.body_count==1,path.name
 assert abs(m.bounds[0][2])<1e-5,path.name
(P/'docs'/'mesh_checks.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
