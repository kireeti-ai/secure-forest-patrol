import type { Metadata } from "next";
import "./globals.css";
import { ClientProviders } from "../components/providers/ClientProviders";

export const metadata: Metadata = {
  title: "Secure Forest Patrol",
  description: "Offline patrol verification for forest areas with limited connectivity",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
