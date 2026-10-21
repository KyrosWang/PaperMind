import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperMind",
  description: "Your self-hosted scientific reading workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="flex h-16 items-center justify-between border-b border-black/10 bg-paper px-6">
          <Link href="/library" className="flex items-baseline gap-2">
            <span className="font-serif text-2xl font-semibold tracking-tight">PaperMind</span>
            <span className="text-xs uppercase tracking-[0.2em] text-moss">Research workspace</span>
          </Link>
          <span className="rounded-full bg-mist px-3 py-1 text-xs font-medium text-moss">Private library</span>
        </header>
        {children}
      </body>
    </html>
  );
}

