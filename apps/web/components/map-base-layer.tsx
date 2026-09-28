"use client";
import { useRef, useState } from "react";
import L from "leaflet";
import { TileLayer } from "react-leaflet";

export function MapBaseLayer() {
  const layer = useRef<L.TileLayer>(null);
  const [failed, setFailed] = useState(false);
  return (
    <>
      <TileLayer
        ref={layer}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        eventHandlers={{ tileerror: () => setFailed(true) }}
      />
      {failed && (
        <div
          role="status"
          className="absolute left-14 top-3 z-[1000] max-w-[55%] rounded border border-warning/40 bg-surface px-3 py-2 text-xs text-warning"
        >
          Some map tiles could not load. Camera locations remain available.{" "}
          <button
            className="underline"
            onClick={() => {
              setFailed(false);
              layer.current?.redraw();
            }}
          >
            Retry map
          </button>
        </div>
      )}
    </>
  );
}
