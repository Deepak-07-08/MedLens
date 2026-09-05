import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { AuthShell, Field, FormError } from "../components/AuthForm";
import { errorMessage, useAuth } from "../lib/auth";

export default function Register() {
  const { user, signUp } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const tooShort = password.length > 0 && password.length < 8;

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      await signUp(email.trim(), password, fullName.trim());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Create an account"
      subtitle="Clinical information, organised."
    >
      <FormError message={error} />

      <Field label="Full name" value={fullName} onChange={setFullName} />
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
        autoComplete="new-password"
        hint={tooShort ? "Use at least 8 characters." : "At least 8 characters."}
      />

      <button
        onClick={submit}
        disabled={busy || !email || password.length < 8}
        className="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium
                   text-white disabled:opacity-40"
      >
        {busy ? "Creating account…" : "Create account"}
      </button>

      <p className="text-sm text-muted">
        Already registered?{" "}
        <Link to="/login" className="text-accent underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
