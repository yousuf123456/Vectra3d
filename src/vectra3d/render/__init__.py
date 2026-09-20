"""Drawing the 3D scene with PyVista.

Everything here runs on the main thread. PyVista and VTK are not thread-safe,
so the tracker thread never reaches into this layer; it sends plain data and
the main thread does the drawing.
"""
