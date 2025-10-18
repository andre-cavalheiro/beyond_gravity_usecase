"use client"

import { createContext, useContext } from "react"
import type { User as UserAuth } from "firebase/auth"
import type { User, Organization } from "@/lib/api/types"

export interface AuthContextType {
  userAuth: UserAuth | null
  user: User | null
  organization: Organization | null
  loading: boolean
  signIn: () => Promise<void>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthContextType>({
  userAuth: null,
  user: null,
  organization: null,
  loading: true,
  signIn: async () => {},
  signOut: async () => {},
})

export const useAuth = () => useContext(AuthContext)
