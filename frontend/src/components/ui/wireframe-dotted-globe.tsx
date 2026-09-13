"use client"

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
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const context = canvas.getContext("2d")
    if (!context) return

    const containerWidth = Math.min(width, window.innerWidth - 40)
    const containerHeight = Math.min(height, window.innerHeight - 100)
    const radius = Math.min(containerWidth, containerHeight) / 2.5

    const dpr = window.devicePixelRatio || 1
    canvas.width = containerWidth * dpr
    canvas.height = containerHeight * dpr
    canvas.style.width = `${containerWidth}px`
    canvas.style.height = `${containerHeight}px`
    context.scale(dpr, dpr)

    const projection = d3
      .geoOrthographic()
      .scale(radius)
      .translate([containerWidth / 2, containerHeight / 2])
      .clipAngle(90)

    const path = d3.geoPath().projection(projection).context(context)
    const graticule = d3.geoGraticule()

    let allDots = new Float32Array(0)
    let landFeatures: any

    const render = () => {
      context.clearRect(0, 0, containerWidth, containerHeight)

      const currentScale = projection.scale()
      const scaleFactor = currentScale / radius
      const centerX = containerWidth / 2
      const centerY = containerHeight / 2

      context.beginPath()
      context.arc(centerX, centerY, currentScale, 0, 2 * Math.PI)
      context.fillStyle = "#000000"
      context.fill()
      context.strokeStyle = "#ffffff"
      context.lineWidth = 2 * scaleFactor
      context.stroke()

      if (!landFeatures) return

      context.beginPath()
      path(graticule())
      context.strokeStyle = "#ffffff"
      context.lineWidth = 1 * scaleFactor
      context.globalAlpha = 0.25
      context.stroke()
      context.globalAlpha = 1

      context.beginPath()
      for (const feature of landFeatures.features) path(feature)
      context.strokeStyle = "#ffffff"
      context.lineWidth = 1 * scaleFactor
      context.stroke()

      context.beginPath()
      context.fillStyle = "#999999"
      const dotRadius = 1.2 * scaleFactor
      const [rotationLng, rotationLat] = projection.rotate()
      const lambda = (rotationLng * Math.PI) / 180
      const phi = (rotationLat * Math.PI) / 180
      const sinLambda = Math.sin(lambda)
      const cosLambda = Math.cos(lambda)
      const sinPhi = Math.sin(phi)
      const cosPhi = Math.cos(phi)

      for (let i = 0; i < allDots.length; i += 3) {
        const x = allDots[i]
        const y = allDots[i + 1]
        const z = allDots[i + 2]
        const visible = x * cosPhi * cosLambda + y * cosPhi * sinLambda + z * sinPhi
        if (visible <= 0) continue

        const screenX = (-x * sinLambda + y * cosLambda) * currentScale + centerX
        const screenY =
          (x * sinPhi * cosLambda + y * sinPhi * sinLambda - z * cosPhi) * currentScale + centerY

        if (screenX < 0 || screenX > containerWidth || screenY < 0 || screenY > containerHeight) continue

        context.moveTo(screenX + dotRadius, screenY)
        context.arc(screenX, screenY, dotRadius, 0, 2 * Math.PI)
      }

      context.fill()
    }

    const loadWorldData = async () => {
      try {
        setIsLoading(true)
        const response = await fetch(
          "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/refs/heads/master/110m/physical/ne_110m_land.json",
        )
        if (!response.ok) throw new Error("Failed to load land data")
        landFeatures = await response.json()

        // Torpağı aşağı ölçülü rasterə çəkib piksel nümunəsindən nöqtələri çıxarırıq.
        // Bu, minlərlə ağır point-in-polygon hesablamasını aradan qaldırır.
        const mapWidth = 360
        const mapHeight = 180
        const sampleStep = 2
        const raster = document.createElement("canvas")
        raster.width = mapWidth
        raster.height = mapHeight
        const rasterContext = raster.getContext("2d")
        if (!rasterContext) throw new Error("Failed to create globe raster")

        const rasterProjection = d3
          .geoEquirectangular()
          .scale(mapWidth / (2 * Math.PI))
          .translate([mapWidth / 2, mapHeight / 2])

        const rasterPath = d3.geoPath().projection(rasterProjection).context(rasterContext)
        rasterContext.clearRect(0, 0, mapWidth, mapHeight)
        rasterContext.fillStyle = "#ffffff"
        rasterContext.beginPath()
        for (const feature of landFeatures.features) rasterPath(feature)
        rasterContext.fill()

        const pixels = rasterContext.getImageData(0, 0, mapWidth, mapHeight).data
        const dotCoordinates: number[] = []

        for (let py = 0; py < mapHeight; py += sampleStep) {
          const lat = 90 - (py / mapHeight) * 180
          const latRad = (lat * Math.PI) / 180
          const cosLat = Math.cos(latRad)
          const sinLat = Math.sin(latRad)

          for (let px = 0; px < mapWidth; px += sampleStep) {
            const pixelIndex = (py * mapWidth + px) * 4
            if (pixels[pixelIndex + 3] === 0) continue

            const lng = (px / mapWidth) * 360 - 180
            const lngRad = (lng * Math.PI) / 180
            dotCoordinates.push(
              cosLat * Math.cos(lngRad),
              cosLat * Math.sin(lngRad),
              sinLat,
            )
          }
        }

        allDots = new Float32Array(dotCoordinates)
        dotCoordinates.length = 0
        render()
        setIsLoading(false)
      } catch (err) {
        setError("Failed to load land map data")
        setIsLoading(false)
      }
    }

    const rotation: [number, number] = [0, 0]
    let autoRotate = true
    const rotationSpeed = 0.5
    let lastFrameTime = 0

    const rotate = (elapsed: number) => {
      if (elapsed - lastFrameTime < 16) return
      lastFrameTime = elapsed

      if (autoRotate) {
        rotation[0] += rotationSpeed
        projection.rotate(rotation)
        render()
      }
    }

    const rotationTimer = d3.timer(rotate)

    const handleMouseDown = (event: MouseEvent) => {
      autoRotate = false
      const startX = event.clientX
      const startY = event.clientY
      const startRotation = [...rotation]

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const sensitivity = 0.5
        const dx = moveEvent.clientX - startX
        const dy = moveEvent.clientY - startY
        rotation[0] = startRotation[0] + dx * sensitivity
        rotation[1] = startRotation[1] - dy * sensitivity
        rotation[1] = Math.max(-90, Math.min(90, rotation[1]))
        projection.rotate(rotation)
        render()
      }

      const handleMouseUp = () => {
        document.removeEventListener("mousemove", handleMouseMove)
        document.removeEventListener("mouseup", handleMouseUp)
        setTimeout(() => {
          autoRotate = true
        }, 10)
      }

      document.addEventListener("mousemove", handleMouseMove)
      document.addEventListener("mouseup", handleMouseUp)
    }

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      const scaleFactor = event.deltaY > 0 ? 0.9 : 1.1
      const newRadius = Math.max(radius * 0.5, Math.min(radius * 3, projection.scale() * scaleFactor))
      projection.scale(newRadius)
      render()
    }

    canvas.addEventListener("mousedown", handleMouseDown)
    canvas.addEventListener("wheel", handleWheel, { passive: false })

    loadWorldData()

    return () => {
      rotationTimer.stop()
      canvas.removeEventListener("mousedown", handleMouseDown)
      canvas.removeEventListener("wheel", handleWheel)
    }
  }, [width, height])

  if (error) {
    return (
      <div className={`dark flex items-center justify-center bg-card rounded-2xl p-8 ${className}`}>
        <div className="text-center">
          <p className="dark text-destructive font-semibold mb-2">Error loading Earth visualization</p>
          <p className="dark text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-auto rounded-2xl bg-background dark"
        style={{ maxWidth: "100%", height: "auto" }}
      />
      <div className="absolute bottom-4 left-4 text-xs text-muted-foreground px-2 py-1 rounded-md dark bg-neutral-900">
        Drag to rotate • Scroll to zoom
      </div>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-xs text-muted-foreground">Loading Earth...</span>
        </div>
      )}
    </div>
  )
}