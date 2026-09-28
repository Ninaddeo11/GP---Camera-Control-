"use client";

import { useHls } from "@/lib/use-hls";
import { useWhep } from "@/lib/use-whep";

/**
 * Picks the live-video transport for this deployment. WHEP (WebRTC) is the
 * default — lower latency, works on the local docker-compose stack since
 * nginx/Docker Desktop can carry WebRTC's UDP media plane there. Set
 * NEXT_PUBLIC_VIDEO_PROTOCOL=hls wherever that isn't true (e.g. Render,
 * which only proxies HTTPS and has no UDP ingress at all — confirmed via
 * Render's own feature-request tracker, not a bug in this app).
 */
export function useCameraFeed(cameraId: string | null) {
  const useHlsProtocol = process.env.NEXT_PUBLIC_VIDEO_PROTOCOL === "hls";
  // eslint-disable-next-line react-hooks/rules-of-hooks -- resolved from a
  // build-time env var, not runtime state, so this never actually
  // conditionally calls a different hook across renders for a given build.
  return useHlsProtocol ? useHls(cameraId) : useWhep(cameraId);
}
