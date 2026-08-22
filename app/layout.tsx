import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hera",
  description: "Inteligência de planejamento curricular e oferta de turmas para a coordenação de Farmácia.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
