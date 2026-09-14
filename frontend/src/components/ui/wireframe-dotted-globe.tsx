import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"

interface RotatingEarthProps {
  width?: number
  height?: number
  className?: string
}

export default function RotatingEarth({ width = 800, height = 600, className = "" }: RotatingEarthProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const context = canvas.getContext("2d")
    if (!context) return

    const dpr = window.devicePixelRatio || 1
    const scaleFactor = Math.min(dpr, 2)
    canvas.width = width * scaleFactor
    canvas.height = height * scaleFactor
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    context.scale(scaleFactor, scaleFactor)

    const centerX = width / 2
    const centerY = height / 2
    const globeRadius = Math.min(width, height) * 0.42

    const projection = d3.geoOrthographic()
      .scale(globeRadius)
      .translate([centerX, centerY])
      .clipAngle(90)
      .precision(0.3)

    const path = d3.geoPath(projection, context)
    const graticule = d3.geoGraticule()
    let landFeatures: any = null
    let animationFrame: number | null = null
    let lastFrameTime = 0
    let isMounted = true

    const render = (time: number) => {
      if (!isMounted) return
      if (time - lastFrameTime < 16) {
        animationFrame = requestAnimationFrame(render)
        return
      }
      lastFrameTime = time

      context.clearRect(0, 0, width, height)

      context.beginPath()
      context.arc(centerX, centerY, globeRadius, 0, Math.PI * 2)
      context.fillStyle = "#000000"
      context.fill()
      context.strokeStyle = "#ffffff"
      context.lineWidth = 1 * scaleFactor
      context.stroke()

      if (!landFeatures) {
        animationFrame = requestAnimationFrame(render)
        return
      }

      context.beginPath()
      path(graticule())
      context.strokeStyle = "rgba(255, 255, 255, 0.22)"
      context.lineWidth = 0.6
      context.stroke()

      context.beginPath()
      for (const feature of landFeatures.features) {
        path(feature)
      }
      context.fillStyle = "#999999"
      context.fill()
      context.strokeStyle = "#ffffff"
      context.lineWidth = 0.9
      context.stroke()

      animationFrame = requestAnimationFrame(render)
    }

    const loadWorldData = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const response = await fetch("./earth_globe.json")
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        if (!isMounted) return

        landFeatures = data
        setIsLoading(false)
        animationFrame = requestAnimationFrame(render)
      } catch (err) {
        if (!isMounted) return
        setError("Yer kürəsinin vizualizasiyası yüklənmədi")
        setIsLoading(false)
      }
    }

    loadWorldData()

    const handleResize = () => {
      if (!isMounted) return
      const newDpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = width * newDpr
      canvas.height = height * newDpr
      context.setTransform(newDpr, 0, 0, newDpr, 0, 0)
    }

    const handleMouseMove = (event: MouseEvent) => {
      if (event.buttons !== 1) return
      const rect = canvas.getBoundingClientRect()
      const dx = event.clientX - rect.left - centerX
      const dy = event.clientY - rect.top - centerY
      const sensitivity = 0.25
      projection.rotate([projection.rotate()[0] + dx * sensitivity, projection.rotate()[1] - dy * sensitivity])
    }

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      const nextScale = projection.scale() * (1 - event.deltaY * 0.001)
      projection.scale(Math.max(globeRadius * 0.7, Math.min(globeRadius * 1.4, nextScale)))
    }

    canvas.addEventListener("mousemove", handleMouseMove)
    canvas.addEventListener("wheel", handleWheel, { passive: false })

    return () => {
      isMounted = false
      if (animationFrame !== null) cancelAnimationFrame(animationFrame)
      canvas.removeEventListener("mousemove", handleMouseMove)
      canvas.removeEventListener("wheel", handleWheel)
    }
  }, [width, height])

  return (
    <div className={`relative ${className}`}>
      <canvas ref={canvasRef} className="block" />
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-white/60">
          Yüklənir...
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-red-400">
          {error}
        </div>
      )}
    </div>
  )
}
