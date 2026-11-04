import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Favorite Pet Entries",
  description: "Share your favorite pet and save your entry in PostgreSQL.",
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
