import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "Knowledge Continuity | Project Knowledge Handover Platform",
  description: "Evidence-linked project knowledge handover platform - Team Web_hunter",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-50 text-slate-900 overflow-hidden">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
