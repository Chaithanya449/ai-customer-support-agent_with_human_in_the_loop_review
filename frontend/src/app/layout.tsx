import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Store Support | Customer Care",
  description: "Order and return support for your online store.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
