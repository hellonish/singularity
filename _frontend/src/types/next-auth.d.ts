import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    /**
     * Set when backend token refresh fails (`RefreshAccessTokenError`) or when
     * Google succeeded but `/auth/google` exchange failed (`BackendSignInError`).
     */
    error?: string;
  }
  interface User {
    id?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    email?: string;
    accessToken?: string;
    refreshToken?: string;
    accessTokenExpires?: number;
    error?: string;
  }
}
