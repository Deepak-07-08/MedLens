type FieldProps = {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  hint?: string;
};

export function Field({
  label,
  type = "text",
  value,
  onChange,
  autoComplete,
  hint,
}: FieldProps) {
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm
                   outline-none focus:border-accent focus:ring-2
                   focus:ring-accent/20"
      />
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="rounded-md border border-red-200 bg-red-50 px-3 py-2
                 text-sm text-red-700"
    >
      {message}
    </p>
  );
}

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold tracking-tight">MedLens</h1>
        <p className="mt-1 text-sm text-muted">{subtitle}</p>

        <div className="mt-8 rounded-lg border border-line p-6">
          <h2 className="text-base font-medium">{title}</h2>
          <div className="mt-5 space-y-4">{children}</div>
        </div>
      </div>
    </main>
  );
}
