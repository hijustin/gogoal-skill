import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GoGoal · 目标任务看板",
  description: "查看项目中的目标、AI 任务、用户任务和管理时间线。",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
