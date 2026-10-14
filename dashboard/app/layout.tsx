import type { Metadata } from "next";
import { DM_Mono, DM_Sans, Newsreader } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({ variable: "--font-dm-sans", subsets: ["latin"] });
const dmMono = DM_Mono({ variable: "--font-dm-mono", subsets: ["latin"], weight: ["400", "500"] });
const newsreader = Newsreader({ variable: "--font-newsreader", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Application Tracker",
  description: "A clear view of your job application pipeline.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="en" className={`${dmSans.variable} ${dmMono.variable} ${newsreader.variable}`}>
    <body>{children}</body>
  </html>;
}
