import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Cổng quản trị · Trợ lý thông tin phường",
  description: "Quản lý tri thức và trợ lý thông tin công dân",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
