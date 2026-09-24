# 02 — Hand Tracking

How a normal webcam becomes a hand-tracking input device.

---

## 1. From webcam image to hand points

### In plain words
The webcam takes many pictures per second. For each picture, a machine-learning model trained on huge numbers of hand images finds your hands and marks 21 points on each one: the wrist, and the joints and tips of every finger. The app only ever works with these 21 points, not with the picture itself.

### Technically
- The app uses **Google's MediaPipe**, specifically its **Gesture Recognizer** task from the MediaPipe Tasks API.
- For each frame it returns, per hand: **21 landmarks** (x, y in normalized image coordinates from 0 to 1, plus a rough relative depth), a **handedness** label, and a **gesture label** from a built-in classifier.
- The pipeline is two-stage: a detector first finds where hands are in the image, then a landmark model locates the 21 points within each hand region.
- Before recognition, the image is mirrored (so it behaves like a selfie camera) and converted from OpenCV's BGR color order to the RGB order MediaPipe expects.
- Up to 2 hands are tracked. Either hand can do every gesture, so handedness labels aren't used.

### How it's implemented
Built in G4.1, in two small modules under `src/vectra3d/tracking/`.

- `camera.py` opens the webcam with `open_camera()`, using Windows' **DirectShow** backend (`cv2.CAP_DSHOW`). OpenCV's default on Windows, Media Foundation, was measured taking 2.5 s to open this laptop's camera; DirectShow took 0.8 s. A camera that is missing or will not open comes back as `None` rather than an error, because running without one is an ordinary situation for this app.
- `tracker_thread.py` holds the loop. Each pass reads one frame, mirrors it with `cv2.flip`, converts it to RGB with `cv2.cvtColor`, and hands it to MediaPipe's `GestureRecognizer.recognize_for_video` with a millisecond timestamp. `create_recognizer()` is the one place the recognizer's options are set; it asks for **two hands**, because MediaPipe's own default is one, which would have made every two-hand gesture impossible. The packaged app's `--check-model` self-test uses the same function, so it proves the exact setup the camera runs with.
- `to_hand_frame()` turns MediaPipe's result into a plain `HandFrame` (`gestures/hand_frame.py`): for each hand, its 21 points as (x, y) and its gesture label. Depth and the left/right label are dropped on purpose — depth because single-camera depth is unreliable (section 2), left/right because either hand can do every gesture. Nothing after this point ever holds a MediaPipe object, which is what lets the gesture logic in G5 be tested with hand-written fake hands.
- Timestamps come from a monotonic clock and are nudged forward by a millisecond if two frames land in the same one, because VIDEO mode rejects a timestamp that does not increase.
- The preview under the 3D view (`ui/camera_preview.py`) draws the picture and, over it, each hand as white lines along the fingers with a blue dot at every point. MediaPipe used to ship a drawing helper for this, but it went with the old `mp.solutions` interface, so the app keeps its own list of which of the 21 points join which. Beside the picture it names each hand's gesture in plain words ("Thumb up", "No gesture"), with two hands labelled by which side of the picture they are on, or says "No hand detected".
- MediaPipe's label for a hand that is visible but not making a known sign is `None` — read from the label file inside the bundled model. Some older documentation calls it `Unknown`.

### Likely questions
- **Does it need a special camera or a GPU?** No. It runs on an ordinary laptop webcam and CPU.
- **Is it recording me?** No. Each image is processed in memory and discarded immediately (see section 6).
- **Why 21 points?** That's MediaPipe's hand model: 1 wrist point plus 4 points for each of the 5 fingers.

---

## 2. The depth problem

### In plain words
A single webcam sees the world flat, like a photo. It's good at telling left from right and up from down, but bad at telling how close your hand is to the screen. So Vectra3D never asks you to push your hand toward the screen. You add depth to a vector by steering it instead.

### Technically
- MediaPipe's per-landmark depth is relative to the wrist, not a true distance from the camera, and it is noisy.
- All gestures therefore use only the image plane (x and y). A newly created vector starts parallel to the screen; the steering joystick rotates it to point toward or away from the viewer.
- This is a deliberate design choice, recorded as a non-goal in the project overview.

### How it's implemented
Built in G4.1 and G5.1.

- Depth is dropped at the boundary: `to_hand_frame()` keeps only each point's x and y, so nothing after the tracker can use it even by accident.
- Every distance in `gestures/hand_metrics.py` is measured in the picture's two dimensions only. A vector's depth comes later from steering (G5.5), never from the hand's distance to the camera.

### Likely questions
- **Couldn't you use two cameras or a depth camera?** Yes, but the goal is to work on any student's laptop with no extra hardware.

---

## 3. Hand scale: working at any distance

### In plain words
Your hand looks bigger when you lean toward the camera and smaller when you sit back. To keep gestures working the same either way, the app measures everything relative to the size of your own hand, like saying "two hand-lengths apart" instead of "20 centimetres apart."

### Technically
- **1 hand-scale unit (hs)** = the distance from the wrist (landmark 0) to the base of the middle finger (landmark 9) in the image.
- Every gesture distance (pinch threshold, dead zone, stretch) is divided by this, making them **scale-invariant**: if you move closer, both the measured distance and the hand scale grow by the same factor, so their ratio stays the same.
- For two-hand gestures, the average of both hands' scales is used.

### How it's implemented
Built in G5.1, in `gestures/hand_metrics.py`.

- `hand_scale()` is the distance from point 0 to point 9, measured with `math.hypot`.
- **The picture's shape has to be corrected first.** MediaPipe gives each point as 0-1 across the width and 0-1 down the height separately, so on a 640x480 picture one unit of x is a third longer than one unit of y. Measured naively, a hand would change size by up to a third just by turning it from upright to sideways. Each frame therefore carries the picture's `aspect` (width divided by height, read from the actual picture rather than assumed), and `to_picture_units()` multiplies x by it, so every distance is in units of the picture's height. A test holds the same hand upright and sideways and gets 0.2 both times.
- The scale is measured from the smoothed points (section 5), so it does not jitter either.
- `average_scale()` gives the mean of two hands' scales, for two-hand measurements. It arrived in G5.2, where the state machine first uses it to decide whether two pinching hands are close enough together to create rather than resize.

### Likely questions
- **Why the wrist to the middle knuckle?** Those points don't move when fingers bend, so the measurement stays stable during gestures.

---

## 4. Detecting a pinch

### In plain words
A pinch is detected when your thumb tip and index fingertip come close together. To stop it from flickering on and off when your fingers hover near the edge, "pinch starts" needs the fingers closer together than "pinch ends" allows them to drift apart.

### Technically
- Pinch distance = distance between thumb tip (landmark 4) and index tip (landmark 8), in hs.
- **Starts** below 0.25 hs; **ends** above 0.35 hs.
- This gap is **hysteresis**, the same idea as a Schmitt trigger in electronics or a thermostat that turns on at 19° and off at 21°. Without it, noise near a single threshold would toggle the state many times per second.
- The pinch point used by gestures is the midpoint between the two fingertips.
- Pinch isn't in MediaPipe's built-in gesture list, so it's computed directly from landmarks.

### How it's implemented
Built in G5.1, in `gestures/hand_metrics.py`.

- `pinch_distance_hs()` divides the thumb-to-index distance by the hand scale. A hand with a scale of zero - which only made-up test data can produce - has no pinch distance rather than a division by zero, and counts as not pinching.
- `next_pinch(was_pinching, distance)` is the hysteresis, as one small function: a pinch starts only below `PINCH_START_HS` and ends only above `PINCH_END_HS`, and landing exactly on either keeps the current state. The thresholds come from `config.py`.
- Because a pinch depends on the frame before, each hand needs a memory. `HandMetrics` keeps one per hand and gives each hand an id. MediaPipe lists hands in no stable order, so every frame the hands are paired with the previous frame's by the nearest wrist, trying both pairings when there are two hands and taking the one where they moved least in total. A hand that disappears is remembered for 0.3 s (spec section 4.4, added in G5.2), so one that reappears in time is matched to its old memory and carries on pinching; after that it is forgotten and comes back as a new hand. A slow frame does not count: only a hand actually missing from a frame can expire.
- `pinch_point()` is the midpoint of the two fingertips.
- The camera preview shows the result: each hand's line says "Pinching" (or, for example, "Victory, pinching", since a pinch is measured from the fingertips and is separate from MediaPipe's gestures).

### Likely questions
- **What if it doesn't detect my pinch?** The thresholds are tunable values, adjusted after real testing. Lighting also matters: the model needs to see your fingers clearly.

---

## 5. Smoothing out shaky hands

### In plain words
Even a steady hand shakes slightly, and the tracking adds its own small jitter. The app smooths the points out, strongly when your hand is still and lightly when it's moving fast, so it feels steady without feeling slow.

### Technically
- Landmarks pass through a **One Euro filter** (Casiez, Roussel, and Vogel, 2012), a low-pass filter whose cutoff frequency adapts to speed: low cutoff at low speed removes jitter, and high cutoff at high speed reduces lag.
- This resolves the usual trade-off of a fixed filter, which is either smooth but laggy or responsive but jittery.
- An exponential moving average is the fallback if the One Euro filter causes problems.

### How it's implemented
Built in G5.1, in `gestures/hand_metrics.py`.

- `OneEuroFilter` is written in the project (about 25 lines) rather than taken from the authors' PyPI package, which would have been a new dependency for very little code. It follows the authors' reference implementation, including that the first value passes through unchanged. It is timed by each frame's own timestamp, because the frame rate is not steady - it drops from about 30 to about 10 frames a second while the 3D view is busy.
- Only the four points the measurements use are smoothed - the wrist, the middle-finger base, and the thumb and index tips - x and y separately, so eight filters per hand. The preview still draws the raw points, showing exactly what the tracker saw.
- The three settings - minimum cutoff 1.0 Hz, speed coefficient β 0.0, derivative cutoff 1.0 Hz - are in `config.py` and the spec's section 9 table. They are the authors' own defaults; their tuning procedure starts β at 0 and raises it with real hands. Until it is tuned, a pinch registers about 0.15 s late.
- Measured on a still point with random shake: the filter leaves 0.295 of the shake, against 0.31 predicted. It costs about 30 microseconds per frame with two hands, against 33 ms between camera frames.

### Likely questions
- **Why not just average the last few frames?** A plain average always lags behind fast movements. The adaptive filter lags much less when you move quickly.

---

## 6. Privacy

### In plain words
Your camera images never leave the laptop and are never saved. The hand-tracking library does send anonymous performance statistics to Google when the laptop is online.

### Technically
- Frames are processed in memory by the tracker thread and discarded; only the 21 landmark positions per hand are passed on.
- Google's MediaPipe privacy notice states that input images are processed on-device and not sent, but that the Tasks APIs send performance and utilization metrics to Google. No off switch is documented. A first-launch notice telling students this was planned and then removed from the project, so the app itself does not display it.
- The app works fully with the internet disconnected; the model file is bundled inside the app.

### How it's implemented
Built in G4.1.

- A frame exists only inside one pass of the tracker's loop and in the preview, which keeps just the latest picture to draw. Nothing writes a frame to disk and nothing sends one anywhere; the app has no code that could.
- The model file is loaded from inside the app through `paths.resource_path()`, so no network access is involved in starting the camera.
- When the window closes, the tracker is stopped and waited for, and the webcam is released in a `finally` block, so the camera light goes off with the app even if the loop ended on an error.

### Likely questions
- **Does it work offline?** Yes, fully.
- **What exactly is sent to Google?** According to Google's notice, performance and usage metrics of the library, not images or video.
