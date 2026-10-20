import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";

import { ExperimentProvider } from "@/components/experiment-context";
import { Shell } from "@/components/shell";

import "./globals.css";

const sans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
});

const serif = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
});

export const metadata: Metadata = {
  title: "Adaptive blood drive scheduling",
  description: "Plan blood donation drives from your inventory, shortages, and a reinforcement-learning simulator.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${serif.variable} font-sans antialiased`}>
        <ExperimentProvider>
          <Shell>{children}</Shell>
        </ExperimentProvider>
      </body>
    </html>
  );
}
