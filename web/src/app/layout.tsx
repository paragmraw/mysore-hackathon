import { Anek_Kannada, Anek_Latin, Noto_Sans, Noto_Sans_Kannada } from "next/font/google";
import { getLocale } from "next-intl/server";
import "./globals.css";

const anekLatin = Anek_Latin({
    subsets: ["latin"],
    variable: "--font-anek-latin",
    display: "swap",
});

const anekKannada = Anek_Kannada({
    subsets: ["latin"],
    variable: "--font-anek-kannada",
    display: "swap",
});

const notoSans = Noto_Sans({
    subsets: ["latin"],
    variable: "--font-noto-sans",
    display: "swap",
});

const notoSansKannada = Noto_Sans_Kannada({
    subsets: ["latin"],
    variable: "--font-noto-sans",
    display: "swap",
});

export default async function RootLayout({
    children,}: LayoutProps<"/">) {
        const locale = await getLocale();

        return (
            <html
            lang={locale}
            className={`${anekLatin.variable} ${anekKannada.variable} ${notoSans.variable} ${notoSansKannada.variable} h-full antialiased`}
            >
                <body className = "flex min-h-full flex-col">{children}</body>
            </html>
        );
    }
