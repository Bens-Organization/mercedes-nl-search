import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mercedes Scientific Product Search",
  description: "Natural language search for medical and scientific products",
  icons: {
    icon: [
      { url: '/icon.png', sizes: '605x605', type: 'image/png' },
    ],
    apple: [
      { url: '/icon.png', sizes: '605x605', type: 'image/png' },
    ],
  },
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
