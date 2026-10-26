# Source provenance

`vendor/RobStride_Control` contains a selected source snapshot from
https://github.com/Seeed-Projects/RobStride_Control at commit
`e0a01d38335972c2fa1dd1e15bb222c4e15e866b`, licensed under MIT.
The original license is retained at `vendor/RobStride_Control/LICENSE`.

The SDK package and ID scanner are included. Position/speed control programs,
motion examples, other language implementations, nested Git history, generated
metadata, and workstation files are omitted. The package's motion CLI entry
points were removed because those programs are not shipped.

Local changes:

- English scanner messages and comments.
- A pySerial AT transport and serial-path selection in the SDK.
- Scanner auto-discovery, response matching, timeout handling and port cleanup.
- pySerial declared as a package dependency.

Serial framing is based on the manufacturer's RS02 manual, page 14:
https://files.seeedstudio.com/products/RobStride/Product%20Literature/RS02/RS02User%20Manual251112.pdf

The local transport passes simulated tests, including that manual's packet
example. A macOS hardware scan opened the adapter but received no motor replies.
This snapshot is a development environment, not a hardware-validated release.
