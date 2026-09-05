import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAuth } from "../lib/auth";

type Health = { status: string; database: string; phase: string };

export default function Dashboard() {
  const { user, signOut } = useAuth();
  const { data } = useQuery<Health>({
    queryKey: ["health"],
    queryFn: async () => (await api.get("/api/health")).data,
    retry: false,
  });

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-line px-6 py-4">
        <span className="font-semibold tracking-tight">MedLens</span>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted">
            {user?.full_name || user?.email} · {user?.role}
          </span>
          <button onClick={signOut} className="text-accent underline">
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-2xl font-semibold tracking-tight">
          You're signed in
        </h1>
        <p className="mt-2 text-muted">
          Patient records arrive in Phase 3. This page proves the token is
          being sent and accepted on every request.
        </p>

        <dl className="mt-8 space-y-2 rounded-lg border border-line p-5 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted">Signed in as</dt>
            <dd>{user?.email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Role</dt>
            <dd>{user?.role}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Database</dt>
            <dd>{data?.database ?? "…"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Phase</dt>
            <dd>{data?.phase ?? "…"}</dd>
          </div>
        </dl>
      </main>
    </div>
  );
}
