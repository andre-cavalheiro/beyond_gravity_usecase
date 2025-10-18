"use client"

import { Sidebar } from "@/components/sidebar"
import { Toaster } from "sonner"
import { useAuth } from "@/lib/auth/context"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { userAuth, user, organization, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // redirect immediately if not authenticated or org is missing
    if (!loading && (!userAuth || !user || !organization)) {
      router.replace("/") // force them back to landing page
    }
  }, [userAuth, user, organization, loading, router])

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
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
      <Toaster position="top-right" richColors closeButton />
    </>
  )
}
