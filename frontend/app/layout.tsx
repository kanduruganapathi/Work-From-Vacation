import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Work From Vacation — Automated Job Search",
  description:
    "AI-powered job search automation across full-time, contract, freelance, and remote roles.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <div className="brand">
            Work From <span>Vacation</span> 🌴
          </div>
          <div className="muted">Your job hunt, on autopilot</div>
        </nav>
        {children}
      </body>
    </html>
  );
}
