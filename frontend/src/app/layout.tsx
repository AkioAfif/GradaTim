
import type { Metadata } from "next";
import { TaskProvider } from "../context/TaskContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "GradaTim",
  description: "AI Personal Manager",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body>
        <TaskProvider>{children}</TaskProvider>
      </body>
    </html>
  );
}
