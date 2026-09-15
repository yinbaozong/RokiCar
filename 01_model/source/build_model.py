"""V7: low battery service hatch, no ornamental armor tower. Units: mm."""
from pathlib import Path
import json
import cadquery as cq
P=Path(__file__).resolve().parents[1]; W=P/'build';O=P/'cad'
for d in [W/'meshes',O,P/'print',P/'images']:d.mkdir(parents=True,exist_ok=True)
CY=11.3586; BOTTOM=35.2; TOP=38.5; MD=8.25; DEPTH=2.15
MAG=[(0,-8.5),(0,31.2)]; KEYS=[(-29.6,23.0),(29.6,23.0)]
def cylinder(x,y,r,z,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
def rounded(w,h,z,depth,r):return cq.Workplane('XY',origin=(0,CY,z)).rect(w,h).extrude(depth).edges('|Z').fillet(r).val()
orig=cq.importers.importStep(str(P/'reference'/'original_shell.step')).val()
body=orig
for x,y in MAG:
 # Demonstrate >=1 mm of original material to the sides and bottom of each
 # recess. The guard stops short of the outside roof; it cannot touch a cavity.
 guard=cylinder(x,y,MD/2+1,35-DEPTH-1,DEPTH+1-.001)
 missing=guard.cut(orig).Volume()
 assert missing<1e-5,('Roof pocket would approach an internal surface',x,y,missing)
 body=body.cut(cylinder(x,y,MD/2,35-DEPTH,DEPTH+.1))
for x,y in KEYS:body=body.fuse(cylinder(x,y,.8,35,1.05))
body=body.clean()

# Thirty-degree ends repeat the original body bevel directions; no round ears.
outline=[(-12,-14),(12,-14),(32,-2.45299),(32,24.326),(10.047,37),(-10.047,37),(-32,24.326),(-32,-2.45299)]
def polywire(points,z):return cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in points],close=True)
w=polywire(outline,BOTTOM)
cap=cq.Solid.extrudeLinear(w,[],cq.Vector(0,0,TOP-BOTTOM)).clean()
# A tapered, body-colored guide surround visually joins the hatch to the roof.
# Clip it to the original upper roof footprint; all material is exterior.
basewire=polywire(outline,35)
lo=basewire.offset2D(2.5)[0]
hi=basewire.offset2D(1.0)[0].translate((0,0,2.7))
surround=cq.Solid.makeLoft([lo,hi],True)
clearance=cq.Solid.extrudeLinear(basewire.offset2D(.30)[0],[],cq.Vector(0,0,5)).translate((0,0,-.05))
roof_face=max([f for f in orig.Faces() if f.geomType()=='PLANE' and abs(f.Center().z-35)<1e-6],key=lambda f:f.Area())
footprint=cq.Solid.extrudeLinear(roof_face.outerWire(),[],cq.Vector(0,0,5))
surround=surround.cut(clearance).intersect(footprint)
# Small, fully open access in the FIXED rim, including its top surface.
# Unlike V6 there is no fixed overhang above the nail approach.
access=cq.Solid.makeBox(14,8,10,cq.Vector(30,6,34.3))
access=cq.Workplane(obj=access).edges('|Z').fillet(.7).val()
body=body.fuse(surround).cut(access).clean()
# Prove the recess floor remains solid, away from internal cavities.
floor_guard=cq.Solid.makeBox(2.2,6,1,cq.Vector(30.8,7,33.3))
assert floor_guard.cut(orig).Volume()<1e-5
# A small softened top rim is tactile and does not create an ornamental ridge.
cap=cq.Workplane(obj=cap).edges('>Z').chamfer(.45).val()
cap=cap.cut(rounded(57.8,29.8,BOTTOM-.1,1.2,1.4))
for x,y in MAG:cap=cap.cut(cylinder(x,y,MD/2,BOTTOM-.05,DEPTH+.05))
for x,y in KEYS:cap=cap.cut(cylinder(x,y,1.05,BOTTOM-.05,1.35))
# A separate underside relief leaves an exposed 2.2 mm-thick lid lip.
relief=cq.Solid.makeBox(12,8,1.2,cq.Vector(30,6,35.1))
cap=cap.cut(relief).clean()
# Rectangular nail envelope can enter horizontally under the LID only.
nail=cq.Solid.makeBox(10,4,1.2,cq.Vector(30.5,8,34.8))
assert nail.intersect(body).Volume()<1e-5
assert nail.intersect(cap).Volume()<1e-5
lip=cq.Solid.makeBox(1.2,4,.5,cq.Vector(30.6,8,36.3))
assert lip.cut(cap).Volume()<1e-5
assert lip.intersect(body).Volume()<1e-5

roof=max([f for f in orig.Faces() if f.geomType()=='PLANE' and abs(f.Center().z-35)<1e-6 and f.innerWires()],key=lambda f:f.Area())
lift=cq.Solid.extrudeLinear(roof.innerWires()[0],[],cq.Vector(0,0,50)).translate((0,0,.00001))
added=body.cut(orig)
report={'nail_approach_interference_mm3':nail.intersect(body.fuse(cap)).Volume(),'version':'V7 small independent lifting lip','magnet_diameter_mm':8,'magnet_thickness_mm':2,'quantity':4,'socket_diameter_mm':MD,'socket_depth_mm':DEPTH,'hatch_above_original_roof_mm':TOP-35,'V2_height_above_roof_mm':12.5,'roof_recess_safety_margin_mm':1.0,'cap_body_overlap_mm3':body.intersect(cap).Volume(),'battery_extraction_obstruction_mm3':added.intersect(lift).Volume(),'finger_scoop':{'nominal_width_mm':8,'original_roof_cut_depth_mm':0.7,'clear_height_mm':2.0,'lid_roof_remaining_mm':2.2,'right_locator_xy':[29.6,23.0]},'note':'Two verified blind exterior roof recesses, small locating pins, a tapered exterior guide surround and one small fully open fixed-rim access and an independent hatch lip alter the original shell. Internal geometry and wheel-edge surfaces are unchanged. Basic CAD checks only; no physical magnetic/print tests.'}
assert report['cap_body_overlap_mm3']<1e-5
assert report['battery_extraction_obstruction_mm3']<1e-5
assembly=cq.Assembly(name='RokiCar_V7_service_hatch');scene=[]
for name,s,col in [('01_shell',body,(.10,.68,.29)),('02_hatch',cap,(.10,.68,.29))]:
 assert s.isValid() and len(s.Solids())==1,name
 cq.exporters.export(s,str(O/(name+'.step')))
 cq.exporters.export(s,str(W/'meshes'/(name+'.stl')),tolerance=.03,angularTolerance=.1)
 printing=s.rotate((0,0,0),(1,0,0),180).translate((0,0,TOP)) if name.startswith('02') else s
 cq.exporters.export(printing,str(P/'print'/(name+'_print.stl')),tolerance=.03,angularTolerance=.1)
 assembly.add(s,name=name,color=cq.Color(*col))
 scene.append({'path':str((W/'meshes'/(name+'.stl')).relative_to(P)),'name':name,'color':col})
assembly.export(str(O/'03_shell_assembly.step'))
coupon=cq.Solid.makeBox(14,14,3.5).cut(cylinder(7,7,MD/2,3.5-DEPTH,DEPTH+.1))
cq.exporters.export(coupon,str(P/'print'/'04_magnet_fit_coupon.stl'),tolerance=.03,angularTolerance=.1)
for i in [0,1,2,3,14]:scene.append({'path':f'reference/render_context/original_{i}.stl','name':f'Original component {i}','color':[.13,.15,.16] if i in [1,2,3] else [.85,.91,.88] if i==14 else [.24,.28,.27]})
(W/'scene.json').write_text(json.dumps({'objects':scene},ensure_ascii=False,indent=2),encoding='utf-8')
(P/'docs'/'cad_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
print('V7 COMPLETE',flush=True)
