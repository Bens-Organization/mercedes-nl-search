import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mercedes Scientific Product Search",
  description: "Natural language search for medical and scientific products",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
