import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import type { NextAuthConfig } from "next-auth";

export const authConfig: NextAuthConfig = {
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // First login: exchange Google id_token for our backend JWT
      if (account?.id_token) {
        try {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id_token: account.id_token }),
            }
          );
          if (res.ok) {
            const data = await res.json();
            token.accessToken = data.access_token;
            token.refreshToken = data.refresh_token;
            token.accessTokenExpires = Date.now() + data.expires_in * 1000;
          } else {
            const errBody = await res.text();
            console.error("Backend auth exchange failed:", res.status, errBody);
          }
        } catch (e) {
          console.error("Backend auth exchange error:", e);
        }
      }

      const expiresAt =
        token.accessTokenExpires != null
          ? Number(token.accessTokenExpires)
          : undefined;
      const shouldRefreshBackend =
        Boolean(token.refreshToken) &&
        (expiresAt == null || Date.now() > expiresAt - 60_000);

      if (shouldRefreshBackend) {
        try {
          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: token.refreshToken }),
            }
          );
          if (res.ok) {
            const data = await res.json();
            token.accessToken = data.access_token;
            token.refreshToken = data.refresh_token;
            token.accessTokenExpires = Date.now() + data.expires_in * 1000;
          } else {
            console.error("Token refresh failed:", res.status);
            delete token.accessToken;
            delete token.accessTokenExpires;
            delete token.refreshToken;
          }
        } catch (e) {
          console.error("Token refresh error:", e);
          // Do not clear tokens on network errors; stale access may 401 until refresh succeeds.
        }
      }

      return token;
    },
    async session({ session, token }) {
      // Forward the access token from the JWT to the client session
      if (token.accessToken) {
        session.accessToken = token.accessToken;
      }
      return session;
    },
  },
  pages: {
    signIn: "/",
  },
  secret: process.env.NEXTAUTH_SECRET,
  trustHost: true,
  debug: process.env.NODE_ENV === "development",
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
