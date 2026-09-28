"use client";

import { useEffect, useRef, useState } from "react";
import type Hls from "hls.js";

const GO2RTC_BASE = process.env.NEXT_PUBLIC_GO2RTC_WHEP_BASE_URL ?? "http://localhost:1984";

export type HlsStatus = "connecting" | "live" | "error";

/**
 * HLS playback against go2rtc's `/api/stream.m3u8` endpoint — the fallback
 * used instead of useWhep's WebRTC/WHEP path wherever the deployment
 * environment can't carry WebRTC's UDP media plane (e.g. Render, which
 * proxies HTTPS only; see NEXT_PUBLIC_VIDEO_PROTOCOL in api-client.ts's
 * neighboring docs). HLS is plain HTTPS GET requests for a playlist plus
 * .ts/.m4s segments, so it works through any HTTP-only proxy WHEP can't.
 *
 * Tradeoff accepted deliberately: HLS's segment-based delivery adds
 * several seconds of latency versus WHEP's sub-second WebRTC path — fine
 * for a monitoring dashboard, not for anything latency-sensitive.
 */
export function useHls(cameraId: string | null) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState<HlsStatus>("connecting");

  useEffect(() => {
    if (!cameraId) return;

    let cancelled = false;
    let hls: Hls | null = null;
    const video = videoRef.current;
    const src = `${GO2RTC_BASE}/api/stream.m3u8?src=${encodeURIComponent(cameraId)}`;

    setStatus("connecting");

    if (!video) return;

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari (and some WebViews) play HLS natively — no library needed.
      video.src = src;
      const onPlaying = () => !cancelled && setStatus("live");
      const onError = () => !cancelled && setStatus("error");
      video.addEventListener("playing", onPlaying);
      video.addEventListener("error", onError);
      return () => {
        cancelled = true;
        video.removeEventListener("playing", onPlaying);
        video.removeEventListener("error", onError);
      };
    }

    (async () => {
      const { default: HlsLib } = await import("hls.js");
      if (cancelled || !video) return;

      if (!HlsLib.isSupported()) {
        setStatus("error");
        return;
      }

      hls = new HlsLib({ lowLatencyMode: true });
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(HlsLib.Events.MANIFEST_PARSED, () => {
        if (!cancelled) video.play().catch(() => {});
      });
      hls.on(HlsLib.Events.FRAG_BUFFERED, () => {
        if (!cancelled) setStatus("live");
      });
      hls.on(HlsLib.Events.ERROR, (_event, data) => {
        if (!cancelled && data.fatal) setStatus("error");
      });
    })();

    return () => {
      cancelled = true;
      hls?.destroy();
    };
  }, [cameraId]);

  return { videoRef, status };
}
