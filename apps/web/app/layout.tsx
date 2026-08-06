import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "规则化投资信号平台",
  description: "四只基金规则化交易与动态仓位管理方案的本地执行平台",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <nav className="flex gap-4 px-8 py-3 border-b text-sm">
          <a href="/">仪表盘</a>
          <a href="/signals">每周信号</a>
          <a href="/trades">交易日志</a>
          <a href="/portfolio">持仓与资金</a>
          <a href="/settings">设置</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
