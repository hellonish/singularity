"use client";

import Image from "next/image";
import { cn } from "@/lib/cn";
import singularityLogo from "@/assets/singularity-logo.png";

type AppLogoMarkProps = {
  className?: string;
  priority?: boolean;
};

/**
 * Geometric Singularity mark. Imported from `src/assets` so the built URL
 * includes a content hash — replace `src/assets/singularity-logo.png` when
 * updating the logo (avoids stale `/_next/image` cache on `/public` paths).
 */
export function AppLogoMark({ className, priority }: AppLogoMarkProps) {
  return (
    <Image
      src={singularityLogo}
      alt="Singularity logo"
      width={256}
      height={256}
      className={cn("object-contain", className)}
      priority={priority}
    />
  );
}
