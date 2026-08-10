import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudPG 控制台",
  description: "AI-Native Serverless PostgreSQL 管理后台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
