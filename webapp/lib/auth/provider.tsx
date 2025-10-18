"use client"

import { useRouter } from "next/navigation"
import { useContext, useEffect, useState } from "react"
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  type User as UserAuth
} from "firebase/auth"
import { getUser, getOrganization, createOrganization } from "@/lib/api/client"
import type { User, Organization } from "@/lib/api/types"
import { auth } from "./firebase"
import { AuthContext } from "./context"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userAuth, setUserAuth] = useState<UserAuth | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [organization, setOrganization] = useState<Organization | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        setUserAuth(null)
        setUser(null)
        setOrganization(null)
        setLoading(false)
        return
      }

      setUserAuth(firebaseUser)

      try {
        let u = await getUser()
        if (!u.id) {
          await createOrganization(firebaseUser.displayName || "New Org")
          u = await getUser()
        }

        const o = await getOrganization()
        setUser(u)
        setOrganization(o)
      } catch (err) {
        console.error("❌ Bootstrap failed:", err)
      } finally {
        setLoading(false)
      }
    })

    return () => unsubscribe()
  }, [])

  const signIn = async () => {
    const provider = new GoogleAuthProvider()
    await signInWithPopup(auth, provider)
  }

  const signOut = async () => {
    await firebaseSignOut(auth)
    router.push("/") 
  }

  return (
    <AuthContext.Provider
      value={{
        userAuth,
        user,
        organization,
        loading,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
