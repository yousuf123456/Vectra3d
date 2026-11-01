# Vectra3D

## [⬇ Download Vectra3D for Windows (setup.exe, 155 MB)](https://github.com/yousuf123456/Vectra3d/releases/latest/download/Vectra3D-0.1.0-setup.exe)

Run the file and follow the steps. No Python and no administrator password are needed. If Windows says "Windows protected your PC", click **More info**, then **Run anyway**: the app is not code-signed. The first launch can take a minute.

---

Vectra3D is a Windows desktop app for first-year university students. It lets you create, move and analyse 3D vectors with your hands through a webcam, while every value updates live. Everything can also be done from the on-screen panels, with no camera.

- **Hand gestures:** pinch and pull to create or resize a vector, pinch and drag to steer it.
- **Exact input:** type components (x, y, z) or magnitude and direction angles (α, β, γ).
- **See the maths:** magnitude, angles, unit vector, components and projections.
- **Operations:** resultant with a head-to-tail animation, and subtraction.

Works offline. Camera images are used only while the app is open and are never saved or sent anywhere by the app. MediaPipe, the hand-tracking library, sends anonymous performance statistics to Google when a network is available.

## For developers

Requires Windows and [uv](https://docs.astral.sh/uv/). Python 3.12 is installed by uv.

```
uv sync                       # install
uv run python -m vectra3d     # run
uv run pytest                 # test
```

How the app works is explained in [`docs/`](docs/).
