"""Read-only STEP cylindrical face audit."""
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

files = [
    r'E:\三轮小车-麦克纳姆林\模型\终版step\底壳.STEP',
    r'E:\三轮小车-麦克纳姆林\外壳设计\RokiCar-V8\cad\01_shell.step',
]
for path in files:
    s = cq.importers.importStep(path).val()
    b = s.BoundingBox()
    print('\nFILE', path, 'BBOX', (b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax), flush=True)
    for i, f in enumerate(s.Faces()):
        if f.geomType() != 'CYLINDER':
            continue
        a = BRepAdaptor_Surface(f.wrapped)
        cy = a.Cylinder()
        p, d = cy.Location(), cy.Axis().Direction()
        b = f.BoundingBox()
        print(i, 'D', round(cy.Radius()*2,4),
              'AX', tuple(round(v,4) for v in (p.X(),p.Y(),p.Z())),
              'DIR', tuple(round(v,4) for v in (d.X(),d.Y(),d.Z())),
              'BBOX', tuple(round(v,4) for v in (b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax)),
              'AREA', round(f.Area(),4), flush=True)
