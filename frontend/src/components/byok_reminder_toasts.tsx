"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useEffect } from "react";
import { toast } from "sonner";
import { usersApi } from "@/lib/api";

const BYOK_TOAST_ID = "byok-required";

/**
 * Purpose: While the user is signed in but has no LLM keys saved, show a persistent top toast
 * directing them to Profile. Dismisses automatically once at least one key exists.
 */
export function ByokReminderToasts() {
  const { data: session, status } = useSession();
  const accessReady =
    status === "authenticated" && Boolean((session as { accessToken?: string } | null)?.accessToken);

  const { data, isLoading, isFetched } = useQuery({
    queryKey: ["llm-credentials"],
    queryFn: () => usersApi.llmCredentials(),
    enabled: accessReady,
  });

  useEffect(() => {
    if (!accessReady || !isFetched || isLoading) return;
    const n = data?.credentials?.length ?? 0;
    if (n > 0) {
      toast.dismiss(BYOK_TOAST_ID);
      return;
    }
    toast.error("Add an LLM API key in Profile before using models.", {
      id: BYOK_TOAST_ID,
      duration: Infinity,
      action: {
        label: "Profile",
        onClick: () => {
          window.location.href = "/profile";
        },
      },
    });
  }, [accessReady, isFetched, isLoading, data?.credentials?.length]);

  return null;
}
