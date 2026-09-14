# Mission: Three-Wheel Omni Car

## Why
Build a cost-effective three-wheel omni car based on Bambu CyberBrick that can carry a phone, camera/servo payload, and be controlled from a phone. Learning the kinematics matters because the chassis will not move correctly unless the wheel layout, motor directions, and control code agree.

## Success looks like
- Model a compact three-wheel chassis from fixed wheel-center coordinates.
- Explain why a desired chassis motion becomes three different wheel speeds.
- Translate joystick commands into motor PWM values on CyberBrick MicroPython.
- Debug wrong wheel directions without redesigning the chassis.

## Constraints
- Keep the design cost-effective and printable.
- Use a three-layer structure: lower mechanical/electrical plate, middle CyberBrick/control plate, upper phone/camera/servo payload.
- Prefer deterministic diagrams, HTML simulation, and code-native artifacts over decorative visuals.

## Out of scope
- Full closed-loop encoder control for the first chassis version.
- FPV video streaming on the first driveable prototype.
