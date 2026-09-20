"""The vectors, the active vector, and every allowed change to them.

This layer is the single source of truth: nothing else in the app stores
vector data. The info panel and the 3D view only display what is here.

It deliberately imports no Qt, PyVista or NumPy, so all of it can be tested
with pytest alone.
"""
