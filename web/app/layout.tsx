import type { Metadata } from "next";
import { Lora, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["500", "600"],
});

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Asisten Hukum Keluarga Islam",
  description:
    "Panduan langkah perkara, kalkulator waris, dan tanya jawab berdasarkan hukum keluarga Islam Indonesia.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id" className={`${lora.variable} ${jakarta.variable} h-full`}>
      <body className="min-h-full">
        <header className="border-b border-line bg-surface">
          <div className="mx-auto max-w-3xl px-6 pt-7 pb-4">
            <div className="flex items-center gap-3">
              <span
                aria-hidden
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-base font-semibold text-white"
              >
                ⚖
              </span>
              <h1 className="text-xl font-semibold sm:text-2xl">Asisten Hukum Keluarga Islam</h1>
            </div>
            <p className="lead mt-2 max-w-xl text-[0.95rem]">
              Panduan langkah perkara, kalkulator waris, dan tanya jawab berdasarkan hukum
              keluarga Islam Indonesia.
            </p>
            <Nav />
          </div>
        </header>

        <main className="mx-auto max-w-3xl px-6 py-8">{children}</main>

        <footer className="mx-auto max-w-3xl px-6 pb-10 text-sm text-muted">
          Informasi umum, bukan nasihat hukum. Untuk perkara Anda, konsultasikan dengan advokat
          atau Posbakum di Pengadilan Agama setempat.
        </footer>
      </body>
    </html>
  );
}
