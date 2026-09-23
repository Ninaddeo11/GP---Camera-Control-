"use client";

import { useEffect, useRef, useState } from "react";

const GO2RTC_BASE = process.env.NEXT_PUBLIC_GO2RTC_WHEP_BASE_URL ?? "http://localhost:1984";

export type WhepStatus = "connecting" | "live" | "error";

/**
 * Minimal WHEP client against go2rtc's WebRTC endpoint, built directly on
 * RTCPeerConnection per the project brief ("no lib needed for basic
 * WHEP") — a single HTTP POST carrying the SDP offer, answered with the
 * SDP answer, exactly the WHEP exchange (no separate signaling channel).
 *
 * Go2rtc API assumption: `POST {base}/api/webrtc?src={cameraId}` with
 * `Content-Type: application/sdp` accepts the offer and returns the
 * answer the same way, as of the pinned image tag (see
 * services/ingestion-config/stream_manager.py's Go2rtcClient for the
 * matching caveat on this project's other go2rtc API assumptions) — this
 * is unverified in a running environment; check here first if a tile
 * never goes live.
 *
 * Known gap: go2rtc has no authentication of its own, so this connects to
 * it directly from the browser — camera_id values only ever reach the
 * browser via the already jurisdiction-scoped /api/cameras list, but a
 * user who somehow learned a camera_id outside that list could still pull
 * its feed directly from go2rtc. Closing this needs an authenticating
 * proxy in front of go2rtc (Phase 10 — see README.md).
 */
export function useWhep(cameraId: string | null) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState<WhepStatus>("connecting");

  useEffect(() => {
    if (!cameraId) return;

    let cancelled = false;
    const pc = new RTCPeerConnection();
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });

    pc.ontrack = (event) => {
      if (videoRef.current && event.streams[0]) {
        videoRef.current.srcObject = event.streams[0];
      }
    };
    pc.onconnectionstatechange = () => {
      if (cancelled) return;
      if (pc.connectionState === "connected") setStatus("live");
      if (pc.connectionState === "failed" || pc.connectionState === "disconnected") setStatus("error");
    };

    setStatus("connecting");

    (async () => {
      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const resp = await fetch(`${GO2RTC_BASE}/api/webrtc?src=${encodeURIComponent(cameraId)}`, {
          method: "POST",
          headers: { "Content-Type": "application/sdp" },
          body: offer.sdp,
        });
        if (!resp.ok) throw new Error(`go2rtc WHEP endpoint returned ${resp.status}`);
        const answerSdp = await resp.text();

        if (cancelled) return;
        await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
      pc.close();
    };
  }, [cameraId]);

  return { videoRef, status };
}
