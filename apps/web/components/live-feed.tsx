"use client";

import { Badge } from "@/components/ui/badge";
import { useWhep } from "@/lib/use-whep";
import { cn } from "@/lib/utils";
import type { CameraOut } from "@/lib/types";

const STATUS_TONE = {
  connecting: "neutral",
  live: "success",
  error: "danger",
} as const;

interface LiveFeedProps {
  camera: CameraOut;
  onExpand?: () => void;
  className?: string;
}

export function LiveFeed({ camera, onExpand, className }: LiveFeedProps) {
  const { videoRef, status } = useWhep(camera.camera_id);

  return (
    <button
      type="button"
      onClick={onExpand}
      className={cn(
        "group relative aspect-video w-full overflow-hidden rounded border border-border bg-surface-muted text-left",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
        className
      )}
    >
      <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />

      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/60 to-transparent p-2">
        <span className="truncate text-xs font-medium text-white">{camera.name}</span>
        <Badge tone={STATUS_TONE[status]}>{status}</Badge>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2">
        <span className="text-xs text-white/80">{camera.department}</span>
      </div>
    </button>
  );
}
