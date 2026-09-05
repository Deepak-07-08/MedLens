import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

/** Wraps any page that requires a signed-in user. */
export default function ProtectedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();

  // Wait for /me to answer, or a refresh would bounce you to login.
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        Loading…
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
