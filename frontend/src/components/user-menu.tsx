"use client";

import { signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";

/**
 * When Google does not provide a picture, show the first letter of the first name
 * (first word of the display name), then the email local part, else "?".
 */
function avatarInitialFromFirstName(
  name: string | null | undefined,
  email: string | null | undefined,
): string {
  const trimmed = name?.trim();
  if (trimmed) {
    const firstWord = (trimmed.split(/\s+/)[0] ?? "").trim();
    if (firstWord) {
      const chars = [...firstWord];
      const letter = chars.find((ch) => /\p{L}/u.test(ch));
      if (letter) return letter.toLocaleUpperCase();
      if (chars[0]) return chars[0].toLocaleUpperCase();
    }
  }
  const local = email?.trim().split("@")[0]?.trim() ?? "";
  if (local) {
    const chars = [...local];
    const letter = chars.find((ch) => /\p{L}|\d/u.test(ch));
    if (letter) return letter.toLocaleUpperCase();
  }
  return "?";
}

function UserAvatarChip({
  imageUrl,
  name,
  email,
}: {
  imageUrl: string | null | undefined;
  name: string | null | undefined;
  email: string | null | undefined;
}) {
  const [loadFailed, setLoadFailed] = useState(false);
  const trimmed = imageUrl?.trim();
  const hasUrl = Boolean(trimmed);

  useEffect(() => {
    setLoadFailed(false);
  }, [trimmed]);

  if (hasUrl && !loadFailed) {
    return (
      <img
        src={trimmed}
        alt={name || "Avatar"}
        onError={() => setLoadFailed(true)}
        className="h-8 w-8 rounded-full object-cover"
      />
    );
  }

  return (
    <div
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700"
      aria-hidden
    >
      {avatarInitialFromFirstName(name, email)}
    </div>
  );
}

export function UserMenu() {
  const { data: session } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);

  const user = session?.user;
  if (!user) return null;

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-full p-1 pr-2 transition-colors hover:bg-black/5"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Account menu for ${user.name || user.email || "user"}`}
      >
        <UserAvatarChip imageUrl={user.image} name={user.name} email={user.email} />
        <svg
          className={`h-4 w-4 text-[#6b7280] transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-xl border border-[#e5e2db] bg-white shadow-xl shadow-black/10">
          {/* User info */}
          <div className="border-b border-[#e5e2db] px-4 py-3">
            <p className="truncate text-sm font-medium text-[#1a1a1a]">
              {user.name || "User"}
            </p>
            <p className="truncate text-sm text-[#6b7280]">{user.email}</p>
          </div>

          {/* Navigation links */}
          <div className="p-1">
            <button
              onClick={() => {
                setOpen(false);
                router.push("/profile");
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-[#6b7280] transition-colors hover:bg-[#f3f4f6] hover:text-[#1a1a1a]"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              Settings
            </button>
          </div>

          {/* Logout */}
          <div className="border-t border-[#e5e2db] p-1">
            <button
              onClick={() => {
                setOpen(false);
                signOut({ callbackUrl: "/" });
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-red-600 transition-colors hover:bg-red-50"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
