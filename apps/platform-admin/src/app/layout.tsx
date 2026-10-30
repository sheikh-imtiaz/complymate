import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { AdminShell } from "@/components/AdminShell";

export const metadata: Metadata = { title: "ComplyMate Platform Admin", robots: { index: false, follow: false }, icons: { icon: "/favicon.ico" } };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-AU">
      <body>
        <Providers>
          <AdminShell>{children}</AdminShell>
        </Providers>
      </body>
    </html>
  );
}
