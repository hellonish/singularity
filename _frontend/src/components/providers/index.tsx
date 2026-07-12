"use client";
import { SessionProvider } from "next-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "sonner";
import { ByokReminderToasts } from "@/components/byok_reminder_toasts";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 60_000, retry: 1 } },
  }));
  return (
    <SessionProvider
      refetchInterval={4 * 60}
      refetchOnWindowFocus
    >
      <QueryClientProvider client={queryClient}>
        <ByokReminderToasts />
        <Toaster position="top-center" richColors closeButton />
        {children}
      </QueryClientProvider>
    </SessionProvider>
  );
}
