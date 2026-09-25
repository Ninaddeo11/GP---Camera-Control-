# Camera gateway contract (confirmed)

This is the organizer-provided integration spec for the real Government
CCTV gateway, kept verbatim so it stays the single source of truth. It
supersedes the earlier "documented assumption" framing in the main
README — every hard constraint below was already implemented against a
guess; this confirms the guess was right and removes the hedging.

Where the code lives for each rule is cross-referenced inline as `→ path`.

---

## 1. What you are connecting to

Every camera is published as a live RTP/RTSP stream. One second of video
takes one second to arrive, frames carry monotonic presentation timestamps
(PTS), and there is no seeking, no byte-range fetching, and no way to run
ahead of real time. Treat each endpoint as you would a physical camera on
an operational network.

| Protocol | Endpoint | Intended for |
|---|---|---|
| RTSP | `rtsp://<host>:8554/stream/<id>` | AI inference (OpenCV, GStreamer, FFmpeg, DeepStream) |
| WebRTC (WHEP) | `http://<host>:8889/stream/<id>/whep` | Low-latency browser preview |
| HLS | `http://<host>/live/stream/<id>/index.m3u8` | Dashboards, mobile, restricted networks |

Always start from the catalogue rather than hard-coding endpoints:

```
curl -s http://<host>/api/ingest
```

It returns every camera with its id, location, codec, live status, stream
properties, and all three URLs. Camera ids and the set of available
cameras can change; **the catalogue is the contract, the URL pattern is
not**.

→ `services/ingestion-config/stream_manager.py` (`CatalogueClient`) and
`services/inference/camera_catalogue_client.py` both read every URL
straight from `/api/ingest` at runtime — no protocol pattern is ever
hardcoded, exactly per this rule. `INGEST_API_URL` is the only thing that
needs to change to point at the real gateway instead of
`services/catalogue-mock` (see `.env.example`).

## 2. Connecting

### OpenCV (Python)

```python
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2

cap = cv2.VideoCapture("rtsp://<host>:8554/stream/1", cv2.CAP_FFMPEG)
while True:
    ok, frame = cap.read()
    if not ok:
        break  # reconnect — see §3
    pts_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
    ...
```

→ `services/inference/camera_source.py` uses this exact pattern
(`OPENCV_FFMPEG_CAPTURE_OPTIONS`, `cv2.CAP_FFMPEG`, `CAP_PROP_POS_MSEC`).

### GStreamer

```
gst-launch-1.0 rtspsrc location=rtsp://<host>:8554/stream/1 protocols=tcp latency=200 \
 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! fakesink
```

For H.265 streams, use `rtph265depay` and `h265parse` instead. Not used in
this repo (OpenCV/FFmpeg covers our decode path), kept here for reference
since the gateway may be probed with it directly during evaluation.

### FFmpeg / ffprobe

```
ffplay -rtsp_transport tcp rtsp://<host>:8554/stream/1
ffprobe -rtsp_transport tcp rtsp://<host>:8554/stream/1
```

### NVIDIA DeepStream

Use `nvurisrcbin` / `uridecodebin` with the RTSP URI and set
`select-rtp-protocol=4` (TCP). Streams are H.264 or H.265; both decode on
`nvv4l2decoder` without CPU demuxing. Not used in this repo — noted for
future GPU-accelerated decode work if OpenCV/FFmpeg CPU decode becomes the
bottleneck at higher camera counts.

## 3. Do's and don'ts

**DO — Force RTSP over TCP.** UDP is accepted but fails across NAT and
most corporate firewalls; partial UDP delivery produces corrupt frames
that look like model bugs. If port 8554 is blocked on your network, use
the HLS endpoint instead.
→ `stream_manager.py` (`_with_tcp_transport`, the go2rtc ingestion leg) and
`camera_source.py` (`OPENCV_FFMPEG_CAPTURE_OPTIONS`, the frame-decode leg).

**DON'T — Trust the reported frame rate.** `CAP_PROP_FPS` often doesn't
match actual delivery; using it for speed/dwell-time math produces wrong
results. Measure the real rate or ignore declared FPS entirely.
→ `camera_source.py` reads `CAP_PROP_FPS` only for a startup log line,
never for scheduling or any time-derived calculation.

**DO — Drive all timing from PTS, never arrival time.** On connect, the
gateway replays its buffered GOP so the decoder can start at a keyframe —
the first second or two may arrive faster than real time. A tracker that
timestamps by arrival computes impossible velocities right after every
connection; trackers must be fed PTS deltas.
→ `camera_source.py` (`CAP_PROP_POS_MSEC` on every frame, passed through
as `frame_pts_ms`); `tracker.py`/`vehicle_trace.py` never use wall-clock
arrival time for anything speed- or dwell-related.

**DON'T — Assume a constant frame rate.** Frame intervals aren't
guaranteed uniform; pipelines must tolerate inter-frame gaps without
treating them as a disconnect.
→ `camera_source.py`'s target-FPS throttle paces processing without
assuming a fixed interval between frames.

**DO — Reconnect automatically, with backoff.** Start at ~2s, cap at
~30s. Never reconnect in a tight loop.
→ `stream_manager.py` (`StreamSupervisor._check_health`) and
`camera_source.py` (`schedule_reconnect`) both implement this
independently, at the ingestion leg and the frame-decode leg respectively.

**DON'T — Treat decode warnings at join as fatal.** Messages like `Error
constructing the frame RPS` or `Could not find ref with POC` before the
first IDR are normal and self-correct.
→ `camera_source.py`'s `MAX_CONSECUTIVE_READ_FAILURES` tolerates a run of
bad/missing frames before treating the camera as disconnected, instead of
reconnecting on the first one.

**DON'T — Assume a uniform grid.** Cameras differ in resolution, codec,
frame rate, and bitrate; read per-camera properties from `/api/ingest` and
size batching/buffers/decoders accordingly.
→ `Camera` (both `stream_manager.py`'s and the registry's `models/camera.py`)
carries `resolution`/`codec`/`fps` straight from the catalogue; nothing
assumes a fixed shape across cameras.

**DO — Expect a scene discontinuity.** Each feed loops; at the loop point
the scene cuts abruptly, like a camera reboot. Long-lived state (track
IDs, background models) must recover from a hard cut, not assume infinite
continuity.
→ `camera_source.py` detects a backward/anomalous PTS jump and reports
`FrameStatus.DISCONTINUITY`; `pipeline.py` responds by calling
`CameraTracker.reset()` (flushing ByteTrack state) and clearing that
camera's ANPR dedup state, so a stale track_id can never survive the cut.

**DON'T — Plan around obtaining copies of the footage.** There is no file
download; `/stream/<id>` is the browser playback fallback and answers
range requests for a media player, so pulling it with `curl`/`wget` yields
a partial file that looks complete. Build against a live capture from the
start.
→ nothing in this repo ever fetches a camera URL with a plain HTTP client
expecting a complete file; every consumer is a streaming client
(`cv2.VideoCapture`, go2rtc, the browser's WHEP/HLS players).

**DON'T — Publish to the gateway. Consume only.**
→ `CatalogueClient` (both copies) only ever issues `GET
/api/ingest`; nothing in this repo calls a gateway control API or
publishes a stream back to it.

**DO — Pace your load.** Open only the cameras you're actively
processing; close captures you're finished with.
→ `stream_manager.py`'s `_reconcile` tears down go2rtc streams for
cameras no longer in the catalogue; `services/inference/main.py` stops and
joins the `CameraWorker` thread (which calls `CameraSource.disconnect()`)
for the same case.

## 4. Pre-submission checklist

- [x] Every client forces RTSP over TCP.
- [x] No timing logic depends on `CAP_PROP_FPS` or frame arrival time.
- [x] Inter-frame gaps do not crash or stall the pipeline.
- [ ] Reconnect with backoff is implemented — **and tested by actually
      restarting a feed**, which needs the real gateway or a live network
      interruption; the mock catalogue's deliberately-unreachable demo
      camera exercises the code path but isn't the same as a live
      interruption.
- [x] Decoder warnings on join are logged, not fatal.
- [x] Camera list and per-camera properties are read from `/api/ingest`.
- [x] Pipeline handles mixed H.264/H.265 and mixed resolutions (OpenCV/
      FFmpeg auto-detect codec; nothing hardcodes one).
- [x] Behaviour is sane across a scene discontinuity.

## 5. Support

Report feed problems with the camera id, the exact URL, client and
version, the UTC timestamp, and the client-side error log. Confirm the
camera's live status in `/api/ingest` before reporting it down.
