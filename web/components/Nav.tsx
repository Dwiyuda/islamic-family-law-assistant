"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tautan = [
  { href: "/", label: "Navigator" },
  { href: "/waris", label: "Kalkulator Waris" },
  { href: "/tanya", label: "Tanya Jawab" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="mt-5 flex flex-wrap gap-1.5">
      {tautan.map((t) => {
        const active = path === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            aria-current={active ? "page" : undefined}
            className={
              "rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors " +
              (active
                ? "bg-primary text-white"
                : "text-ink-soft hover:bg-primary-soft hover:text-primary-strong")
            }
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
