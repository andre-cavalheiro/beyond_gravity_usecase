"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { Toaster } from "sonner"
import { useAuth } from "@/lib/auth/context"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { PlayCircle, X } from "lucide-react"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { userAuth, user, organization, loading } = useAuth()
  const router = useRouter()
  const [showBanner, setShowBanner] = useState(false)
  const bannerStorageKey = "demoVideoBanner:dismissed"

  useEffect(() => {
    // redirect immediately if not authenticated or org is missing
    if (!loading && (!userAuth || !user || !organization)) {
      router.replace("/") // force them back to landing page
    }
  }, [userAuth, user, organization, loading, router])

  useEffect(() => {
    const dismissed = typeof window !== "undefined" ? window.localStorage.getItem(bannerStorageKey) : "false"
    setShowBanner(dismissed !== "true")
  }, [])

  const handleDismissBanner = () => {
    setShowBanner(false)
    if (typeof window !== "undefined") {
      window.localStorage.setItem(bannerStorageKey, "true")
    }
  }

  if (loading || !userAuth || !user || !organization) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span className="text-muted-foreground">Loading your account...</span>
      </div>
    )
  }

  return (
    <>
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 p-6 overflow-auto">
          {showBanner && (
            <div className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-sky-200 bg-sky-50/90 px-4 py-3 text-sky-900 shadow-sm">
              <div className="flex gap-3">
                <PlayCircle className="mt-0.5 h-5 w-5 text-sky-600" />
                <div>
                  <p className="text-sm font-semibold">Take a quick tour</p>
                  <a
                    href="https://www.youtube.com/watch?v=GKOW-V0tz9c"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-flex text-sm font-medium text-sky-700 hover:text-sky-800 hover:underline"
                  >
                    Watch the 8-minute demo video
                  </a>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleDismissBanner}
                className="h-7 w-7 text-sky-600 hover:text-sky-800"
              >
                <X className="h-4 w-4" />
                <span className="sr-only">Dismiss demo banner</span>
              </Button>
            </div>
          )}
          {children}
        </main>
      </div>
      <Toaster position="top-right" richColors closeButton />
    </>
  )
}
