import type { Metadata } from "next";
import { Inter, Tajawal } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const tajawal = Tajawal({ weight: ["300", "400", "500", "700"], subsets: ["arabic"], variable: "--font-tajawal" });

export const metadata: Metadata = {
  title: "Chatlytics — Conversational Analytics",
  description: "Open-source conversational analytics: ask questions in natural language, get deterministic answers backed by Python.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // Defaulting to English LTR. We'll manage RTL switching via client state in the main page.
    <html lang="en" dir="ltr">
      <body className={`${inter.variable} ${tajawal.variable} font-sans`} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
