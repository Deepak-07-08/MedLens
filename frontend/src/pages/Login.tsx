import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { AuthShell, Field, FormError } from "../components/AuthForm";
import { errorMessage, useAuth } from "../lib/auth";

export default function Login() {
  const { user, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      await signIn(email.trim(), password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Sign in" subtitle="Clinical information, organised.">
      <FormError message={error} />

      <Field
        label="Email"
        type="email"
        value={email}
        onChange={setEmail}
        autoComplete="email"
      />
      <Field
        label="Password"
        type="password"
        value={password}
        onChange={setPassword}
        autoComplete="current-password"
      />

      <button
        onClick={submit}
        disabled={busy || !email || !password}
        className="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium
                   text-white disabled:opacity-40"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>

      <p className="text-sm text-muted">
        No account?{" "}
        <Link to="/register" className="text-accent underline">
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}
