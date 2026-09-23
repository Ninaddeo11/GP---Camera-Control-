"use client";

import { useEffect, useRef, useState } from "react";

import { apiBaseUrl, getAccessToken } from "./api-client";
import type { WatchlistAlertMessage } from "./types";

const RECONNECT_DELAY_MS = 3000;

/**
 * Live watchlist alert feed over WebSocket. Reconnects with a fixed delay
 * on drop (the connection carries no per-request state to preserve, so a
 * simple fixed retry is enough — unlike the camera ingestion paths, which
 * need real exponential backoff because they're guarding a scarce
 * external resource).
 */
export function useAlertStream(onAlert: (alert: WatchlistAlertMessage) => void) {
  const [connected, setConnected] = useState(false);
  const onAlertRef = useRef(onAlert);
  onAlertRef.current = onAlert;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      const token = getAccessToken();
      if (!token || cancelled) return;

      const wsBase = apiBaseUrl().replace(/^http/, "ws");
      socket = new WebSocket(`${wsBase}/alerts/stream?token=${encodeURIComponent(token)}`);

      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
      socket.onerror = () => socket?.close();
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WatchlistAlertMessage;
          if (data.type === "watchlist_match") onAlertRef.current(data);
        } catch {
          // ignore malformed frames
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { connected };
}
