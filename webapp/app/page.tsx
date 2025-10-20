"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/lib/auth/context"
import { Button } from "@/components/ui/button"

function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext("2d")

    if (!canvas || !context) {
      return
    }

    let animationFrameId: number
    const PARTICLE_BASE_COUNT = 90
    const PARTICLE_SPEED = 0.15
    let viewportWidth = 0
    let viewportHeight = 0

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect()
      viewportWidth = rect.width || window.innerWidth
      viewportHeight = rect.height || window.innerHeight

      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.round(viewportWidth * dpr)
      canvas.height = Math.round(viewportHeight * dpr)
      canvas.style.width = `${viewportWidth}px`
      canvas.style.height = `${viewportHeight}px`
      context.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    resizeCanvas()

    type Particle = {
      x: number
      y: number
      vx: number
      vy: number
      radius: number
    }

    const particles: Particle[] = []

    const seedParticles = () => {
      if (!viewportWidth || !viewportHeight) {
        return
      }

      particles.length = 0
      const dynamicCount = Math.floor(
        PARTICLE_BASE_COUNT * Math.min(viewportWidth / 1024 + 0.4, 1.6)
      )

      for (let i = 0; i < dynamicCount; i += 1) {
        particles.push({
          x: Math.random() * viewportWidth,
          y: Math.random() * viewportHeight,
          vx: (Math.random() - 0.5) * PARTICLE_SPEED * viewportWidth * 0.002,
          vy: (Math.random() - 0.5) * PARTICLE_SPEED * viewportHeight * 0.002,
          radius: Math.random() * 1.6 + 0.4,
        })
      }
    }

    seedParticles()

    const drawParticles = () => {
      if (!viewportWidth || !viewportHeight) {
        animationFrameId = window.requestAnimationFrame(drawParticles)
        return
      }

      context.clearRect(0, 0, viewportWidth, viewportHeight)

      particles.forEach((particle) => {
        particle.x += particle.vx
        particle.y += particle.vy

        if (particle.x < 0) {
          particle.x = viewportWidth
        } else if (particle.x > viewportWidth) {
          particle.x = 0
        }

        if (particle.y < 0) {
          particle.y = viewportHeight
        } else if (particle.y > viewportHeight) {
          particle.y = 0
        }

        const depthFactor = 0.4 + particle.radius * 0.4
        const red = Math.round(120 + depthFactor * 60)
        const green = Math.round(160 + depthFactor * 60)
        const blue = 255
        const alpha = 0.28 + depthFactor * 0.35

        context.beginPath()
        context.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2)
        context.fillStyle = `rgba(${red}, ${green}, ${blue}, ${alpha})`
        context.fill()
      })

      for (let i = 0; i < particles.length; i += 1) {
        context.lineWidth = 0.8
        for (let j = i + 1; j < particles.length; j += 1) {
          const particleA = particles[i]
          const particleB = particles[j]
          const dx = particleA.x - particleB.x
          const dy = particleA.y - particleB.y
          const distance = Math.sqrt(dx * dx + dy * dy)

          if (distance < 160) {
            const linkAlpha = 0.26 * (1 - distance / 160)

            context.beginPath()
            context.moveTo(particleA.x, particleA.y)
            context.lineTo(particleB.x, particleB.y)
            context.strokeStyle = `rgba(120, 160, 255, ${linkAlpha})`
            context.stroke()
          }
        }
      }

      animationFrameId = window.requestAnimationFrame(drawParticles)
    }

    const handleResize = () => {
      resizeCanvas()
      seedParticles()
    }

    window.addEventListener("resize", handleResize)
    animationFrameId = window.requestAnimationFrame(drawParticles)

    return () => {
      window.cancelAnimationFrame(animationFrameId)
      window.removeEventListener("resize", handleResize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-0 h-full w-full opacity-90"
    />
  )
}

export default function LandingPage() {
  const { userAuth, user, organization, signIn, loading } = useAuth()
  const router = useRouter()
  const isAuthenticated = Boolean(userAuth && user && organization)
  const isBootstrapping =
    loading || (userAuth && (!user || !organization))

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/home")
    }
  }, [isAuthenticated, router])

  if (isBootstrapping) {
    return (
      <div className="relative flex min-h-screen flex-col overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
        <ParticleField />
        <main className="relative z-10 flex flex-1 items-center justify-center px-6 py-20">
          <div className="flex flex-col items-center gap-4 text-center">
            <Loader2 className="h-10 w-10 animate-spin text-indigo-200" />
            <p className="text-base text-slate-300 sm:text-lg">
              Preparing your workspace…
            </p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <ParticleField />
      <main className="relative z-10 flex flex-1 items-center justify-center px-6 py-20">
        <div className="flex max-w-3xl flex-col items-center gap-8 text-center">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight drop-shadow-sm sm:text-5xl md:text-6xl">
            <span className="block bg-gradient-to-r from-sky-300 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Beyond Gravity's
            </span>
            <span className="mt-2 block text-slate-200">Earthquake Monitoring System</span>
          </h1>
          <p className="max-w-2xl text-base text-slate-300 sm:text-lg">
            By André Cavalheiro
          </p>
          <Button
            onClick={signIn}
            size="lg"
            className="cursor-pointer rounded-full bg-indigo-500/90 px-8 text-slate-50 shadow-xl shadow-indigo-900/40 transition-transform hover:-translate-y-0.5 hover:bg-indigo-400/90 focus-visible:ring-indigo-300"
          >
            Sign in with Google
          </Button>
          <div className="w-full max-w-3xl overflow-hidden rounded-3xl border border-slate-800/60 bg-slate-950/60 shadow-2xl shadow-indigo-900/40">
            <div className="relative aspect-video w-full">
              <iframe
                src="https://www.youtube.com/embed/GKOW-V0tz9c?si=9OFPrdJOAtuV3YJ4"
                title="Beyond Gravity Demo"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                className="absolute inset-0 h-full w-full border-0"
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
