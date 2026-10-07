"""RokiCar V8: no locator pins, one magnet pair, printable guide rim. mm."""
from pathlib import Path
import json
import cadquery as cq

P = Path(__file__).resolve().parents[1]
W, O = P/'build', P/'cad'
for d in (W/'meshes', O, P/'print', P/'images', P/'docs'):
    d.mkdir(parents=True, exist_ok=True)
CY = 11.3586
ROOF, BOTTOM, TOP = 35.0, 35.2, 38.5
MD, DEPTH = 8.40, 2.10
MAG = [(0.0, 31.2)]  # One location; one shell magnet + one lid magnet.
CLEARANCE = 0.40  # Per side; 0.80 mm total across opposite guides.
RIM_WALL = 1.60
RIM_TOP = 37.40
SUPPORT_Z = 31.80
outline = [(-12,-14),(12,-14),(32,-2.45299),(32,24.326),
           (10.047,37),(-10.047,37),(-32,24.326),(-32,-2.45299)]

def cylinder(x,y,r,z,h):
    return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))

def polywire(points,z):
    return cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in points],close=True)

def rounded(w,h,z,depth,r):
    return cq.Workplane('XY',origin=(0,CY,z)).rect(w,h).extrude(depth).edges('|Z').fillet(r).val()

print('Building RokiCar V8', flush=True)
orig = cq.importers.importStep(str(P/'reference'/'original_shell.step')).val()
roof = max([f for f in orig.Faces() if f.geomType()=='PLANE'
            and abs(f.Center().z-ROOF)<1e-6],key=lambda f:f.Area())
basewire = polywire(outline,ROOF)
inner_wire = basewire.offset2D(CLEARANCE)[0]
outer_wire = basewire.offset2D(CLEARANCE+RIM_WALL)[0]
# Complete vertical wall: do not clip it to the old roof footprint. Clipping
# the previous tapered rim made the angled rear edges almost disappear.
surround = cq.Solid.extrudeLinear(outer_wire,[inner_wire],cq.Vector(0,0,RIM_TOP-ROOF))
# A gradual exterior transition supports the portions slightly beyond the old
# roof outline. Its slope is 1.60/3.20 = 0.5 (26.6 degrees from vertical).
support_outer = cq.Solid.makeLoft([
    inner_wire.translate((0,0,SUPPORT_Z-ROOF)),outer_wire],True)
support_void = cq.Solid.extrudeLinear(
    inner_wire.translate((0,0,SUPPORT_Z-ROOF-.01)),[],
    cq.Vector(0,0,ROOF-SUPPORT_Z+.02))
support = support_outer.cut(support_void)

# A filled envelope of the original outer section is used only as a guard.
# Added material within this envelope but outside the original part would be
# an unwanted change to the internal cavity/roof underside.
section = cq.Workplane('XY').newObject([orig]).section(SUPPORT_Z).val()
section_wires = section.Wires()
outer_section = max(section_wires,key=lambda w:cq.Face.makeFromWires(w).Area())
external_envelope = cq.Solid.makeLoft([outer_section,roof.outerWire()],True)
support_internal_intrusion = support.cut(orig).intersect(external_envelope).Volume()
assert support_internal_intrusion<1e-5, ('Support intrudes into original cavity',support_internal_intrusion)

body = orig
for x,y in MAG:
    guard=cylinder(x,y,MD/2+1.0,ROOF-DEPTH-1.0,DEPTH+1.0-.001)
    assert guard.cut(orig).Volume()<1e-5, 'Magnet pocket would approach original internal surface'
    body=body.cut(cylinder(x,y,MD/2,ROOF-DEPTH,DEPTH+.1))
# No locator pin solids are generated. Only one magnet recess is cut.
body=body.fuse(support).fuse(surround)
access=cq.Solid.makeBox(14,8,10,cq.Vector(30,6,34.3))
access=cq.Workplane(obj=access).edges('|Z').fillet(.7).val()
body=body.cut(access).clean()
floor_guard=cq.Solid.makeBox(2.2,6,1,cq.Vector(30.8,7,33.3))
assert floor_guard.cut(orig).Volume()<1e-5

cap=cq.Solid.extrudeLinear(polywire(outline,BOTTOM),[],cq.Vector(0,0,TOP-BOTTOM))
cap=cq.Workplane(obj=cap).edges('>Z').chamfer(.45).val()
cap=cap.cut(rounded(57.8,29.8,BOTTOM-.1,1.2,1.4))
for x,y in MAG:
    cap=cap.cut(cylinder(x,y,MD/2,BOTTOM-.05,DEPTH+.05))
# No matching pin holes in the lid.
relief=cq.Solid.makeBox(12,8,1.2,cq.Vector(30,6,35.1))
cap=cap.cut(relief).clean()

nail=cq.Solid.makeBox(10,4,1.2,cq.Vector(30.5,8,34.8))
lip=cq.Solid.makeBox(1.2,4,.5,cq.Vector(30.6,8,36.3))
assert nail.intersect(body.fuse(cap)).Volume()<1e-5
assert lip.cut(cap).Volume()<1e-5 and lip.intersect(body).Volume()<1e-5
lift=cq.Solid.extrudeLinear(roof.innerWires()[0],[],cq.Vector(0,0,50)).translate((0,0,.00001))
added=body.cut(orig)
removed=orig.cut(body)
allowed_removal=access
for x,y in MAG:
    allowed_removal=allowed_removal.fuse(cylinder(x,y,MD/2,ROOF-DEPTH,DEPTH+.1))
unexpected_removal=removed.cut(allowed_removal).Volume()
assert unexpected_removal<1e-5
assert added.intersect(lift).Volume()<1e-5
assert body.intersect(cap).Volume()<1e-5
# Check real material through both long sides, outside the deliberate nail
# access. The previous footprint-clipped rim could not satisfy these checks.
rim_samples=[]
for z in [35.3,36.4,37.2]:
    for x in [-32,32]:
        for y in [0,20]:
            x0=x+CLEARANCE if x>0 else x-CLEARANCE-RIM_WALL
            probe=cq.Solid.makeBox(RIM_WALL-.02,1,.1,cq.Vector(x0+.01,y-.5,z))
            missing=probe.cut(body).Volume()
            assert missing<1e-5, ('Guide wall missing',x,y,z,missing)
            rim_samples.append({'side_x_mm':x,'y_mm':y,'z_mm':z,'missing_mm3':missing})

report={
 'version':'RokiCar V8 — no pins, single magnet pair, reinforced guide rim',
 'locator_pin_count':0,'lid_locator_hole_count':0,
 'magnet_position_count':1,'magnet_positions_xy_mm':MAG,'magnet_quantity_total':2,
 'magnet_diameter_mm':8,'magnet_thickness_mm':2,
 'socket_diameter_mm':MD,'socket_depth_mm':DEPTH,
 'socket_diameter_clearance_mm':MD-8,'socket_depth_allowance_mm':DEPTH-2,
 'lid_guide_clearance_per_side_mm':CLEARANCE,
 'lid_guide_total_clearance_mm':2*CLEARANCE,
 'nominal_lid_roof_gap_mm':BOTTOM-ROOF,
 'rim_wall_mm':RIM_WALL,'rim_height_above_roof_mm':RIM_TOP-ROOF,
 'exterior_support_height_mm':ROOF-SUPPORT_Z,
 'minimum_lid_material_above_magnet_mm':TOP-BOTTOM-DEPTH,
 'roof_recess_safety_margin_mm':1.0,
 'support_internal_intrusion_mm3':support_internal_intrusion,
 'unexpected_original_material_removed_mm3':unexpected_removal,
 'cap_body_overlap_mm3':body.intersect(cap).Volume(),
 'battery_extraction_obstruction_mm3':added.intersect(lift).Volume(),
 'nail_approach_interference_mm3':nail.intersect(body.fuse(cap)).Volume(),
 'rim_sample_checks':rim_samples,
 'note':'Original internal mounting and wheel structure unchanged. Complete 1.6 mm guide walls and a supported exterior transition replace the clipped thin taper. FDM clearances are design allowances, not a guarantee for every printer or magnet. Physical slicing/fit is for user review.'
}
assembly=cq.Assembly(name='RokiCar_V8_single_magnet_hatch')
scene=[]
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
for i in [0,1,2,3,14]:
    scene.append({'path':f'reference/render_context/original_{i}.stl','name':f'Original component {i}',
                  'color':[.13,.15,.16] if i in [1,2,3] else [.85,.91,.88] if i==14 else [.24,.28,.27]})
(W/'scene.json').write_text(json.dumps({'objects':scene},ensure_ascii=False,indent=2),encoding='utf-8')
(P/'docs'/'cad_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
print('V8 COMPLETE',flush=True)
