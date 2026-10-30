export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-white p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" className="h-9 w-9" />
          <span className="text-2xl font-semibold text-brand-700">ComplyMate</span>
        </div>
        {children}
        <p className="mt-6 text-center text-xs text-slate-400">General information, not legal advice.</p>
      </div>
    </main>
  );
}
