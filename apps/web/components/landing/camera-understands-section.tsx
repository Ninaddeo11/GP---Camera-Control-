"use client";

import { Reveal } from "./reveal";

export function CameraUnderstandsSection() {
  return (
    <section id="platform" className="py-24 sm:py-28">
      <div className="mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            A CAMERA SEES.
            <br />
            <span className="text-lp-primary-2">SENTINEL UNDERSTANDS.</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-lp-text-1">
            GP Sentinel turns visual information into context, connecting what
            happened, where it happened and how events relate across the
            environment.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
