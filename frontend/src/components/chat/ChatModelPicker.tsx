"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown } from "lucide-react";
import type { LlmCatalogModel } from "@/lib/api";
import { cn } from "@/lib/cn";

const PROVIDER_LABELS: Record<string, string> = {
  grok: "xAI Grok",
  gemini: "Google Gemini",
  deepseek: "DeepSeek",
};

export type ChatModelPickerGroup = readonly [string, LlmCatalogModel[]];

interface ChatModelPickerProps {
  /** Ordered provider groups from the filtered BYOK catalog. */
  groups: ChatModelPickerGroup[];
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
}

/**
 * Purpose: Custom model selector for chat — grouped by provider, keyboard-friendly via Radix.
 * Inputs: Eligible models (already filtered server-side), current model_id, change handler.
 * Outputs: Trigger + dropdown. Parent hides this when the catalog is empty.
 */
export function ChatModelPicker({
  groups,
  value,
  onChange,
  disabled = false,
}: ChatModelPickerProps) {
  const flat = groups.flatMap(([, items]) => items);
  const current = flat.find((m) => m.model_id === value);

  if (flat.length === 0) return null;

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild disabled={disabled}>
        <button
          type="button"
          className={cn(
            "inline-flex min-w-0 max-w-[min(100%,16rem)] flex-1 items-center justify-between gap-1.5 rounded-lg border border-neutral-200/90 bg-white py-1.5 pl-2.5 pr-2 text-left text-xs font-medium text-neutral-800 shadow-sm outline-none transition-colors",
            "hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-neutral-400/40",
            disabled && "cursor-not-allowed opacity-40",
          )}
          aria-label="Response model"
        >
          <span className="min-w-0 truncate">{current?.display_name ?? value}</span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-neutral-500" strokeWidth={2} aria-hidden />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="z-[80] max-h-[min(320px,70vh)] min-w-[var(--radix-dropdown-menu-trigger-width)] max-w-[min(calc(100vw-2rem),20rem)] overflow-y-auto rounded-xl border border-neutral-200/90 bg-white p-1 shadow-lg"
          sideOffset={4}
          align="start"
          collisionPadding={12}
        >
          {groups.map(([prov, items]) => (
            <div key={prov} className="py-0.5">
              <DropdownMenu.Label className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
                {PROVIDER_LABELS[prov] ?? prov}
              </DropdownMenu.Label>
              {items.map((m) => (
                <DropdownMenu.Item
                  key={m.model_id}
                  className={cn(
                    "flex cursor-pointer select-none items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-neutral-800 outline-none",
                    "data-[highlighted]:bg-neutral-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-40",
                  )}
                  onSelect={() => onChange(m.model_id)}
                >
                  <span className="min-w-0 flex-1 leading-snug">{m.display_name}</span>
                  {m.model_id === value ? (
                    <Check className="h-3.5 w-3.5 shrink-0 text-neutral-700" strokeWidth={2} aria-hidden />
                  ) : null}
                </DropdownMenu.Item>
              ))}
            </div>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
