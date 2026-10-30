import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-slate-500">The page you&apos;re looking for doesn&apos;t exist or you don&apos;t have access.</p>
      <Link href="/dashboard" className="text-brand-600 hover:underline">Back to dashboard</Link>
    </main>
  );
}
