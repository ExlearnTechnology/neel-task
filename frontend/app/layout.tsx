import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EC2 Compose Reference",
  description: "Next.js, FastAPI, and PostgreSQL deployed with Docker Compose on EC2.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
