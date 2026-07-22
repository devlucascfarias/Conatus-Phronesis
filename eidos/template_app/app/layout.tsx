import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Eidos Template",
  description: "Base app para o harness de avaliação do Conatus Eidos",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
