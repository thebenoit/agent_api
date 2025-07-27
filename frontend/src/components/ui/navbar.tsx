"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Navbar() {
    const pathname = usePathname();

    return (
        <div className="border-b bg-white px-4 sm:px-6 md:px-8 lg:px-12 py-3 sm:py-4 md:py-6">
            <div className="w-full max-w-6xl mx-auto flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 sm:gap-3">
                    <img
                        src="/Moveout_Logo2.svg"
                        alt="MoveoutAI Logo"
                        className="w-7 h-7 sm:w-8 sm:h-8 md:w-10 md:h-10"
                    />
                    <span className="font-semibold text-black text-xs sm:text-sm md:text-base">Moveout</span>
                </Link>
                <div className="flex gap-2 sm:gap-3 md:gap-4">
                    {pathname === "/login" ? (
                        <Link href="/signup" className="px-2 sm:px-4 md:px-6 py-1.5 sm:py-2 md:py-3 text-xs sm:text-sm md:text-base bg-black text-white rounded-lg hover:bg-gray-800 transition-colors">
                            S&apos;inscrire
                        </Link>
                    ) : pathname === "/signup" ? (
                        <Link href="/login" className="px-2 sm:px-4 md:px-6 py-1.5 sm:py-2 md:py-3 text-xs sm:text-sm md:text-base border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                            Se connecter
                        </Link>
                    ) : (
                        <>
                            <Link href="/login" className="px-2 sm:px-4 md:px-6 py-1.5 sm:py-2 md:py-3 text-xs sm:text-sm md:text-base border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                                Se connecter
                            </Link>
                            <Link href="/signup" className="px-2 sm:px-4 md:px-6 py-1.5 sm:py-2 md:py-3 text-xs sm:text-sm md:text-base bg-black text-white rounded-lg hover:bg-gray-800 transition-colors">
                                Commencer
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
} 