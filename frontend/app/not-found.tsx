import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-[70vh] place-items-center text-center">
      <div><p className="font-serif text-5xl">Paper not found</p><Link href="/library" className="mt-4 inline-block text-sm text-moss underline">Return to the library</Link></div>
    </main>
  );
}

