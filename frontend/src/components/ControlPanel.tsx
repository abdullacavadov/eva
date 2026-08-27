import { useEffect, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCamera, faMicrophone, faPause, faPlay, faPowerOff, faXmark } from '@fortawesome/free-solid-svg-icons'
import '../styles/control-panel.css'

type ControlCommand = 'shutdown' | 'pause' | 'camera' | 'microphone'

interface ControlPanelProps {
  onCommand: (command: ControlCommand) => void
  paused: boolean
  cameraActive: boolean
  microphoneMuted: boolean
  disabled?: boolean
}

const controls = [
  { command: 'shutdown' as const, label: 'SÖNDÜR', icon: faPowerOff, tone: 'danger' },
  { command: 'pause' as const, label: 'FASİLƏ', icon: faPause, tone: 'warning' },
  { command: 'camera' as const, label: 'KAMERA', icon: faCamera, tone: 'camera' },
  { command: 'microphone' as const, label: 'MİKRAFON', icon: faMicrophone, tone: 'microphone' },
]

export function ControlPanel({ onCommand, paused, cameraActive, microphoneMuted, disabled = false }: ControlPanelProps) {
  const [cameraModalOpen, setCameraModalOpen] = useState(false)
  const [cameraClosing, setCameraClosing] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const closeTimerRef = useRef<number | null>(null)

  const stopLocalCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
  }

  useEffect(() => {
    if (!cameraModalOpen) return
    setCameraError(null)
    let cancelled = false
    navigator.mediaDevices?.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false,
    }).then((stream) => {
      if (cancelled) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        void videoRef.current.play()
      }
    }).catch((error) => {
      console.error('[EVA] Kamera görüntüsü açıla bilmədi:', error)
      if (!cancelled) setCameraError('Kameraya giriş icazəsi alınmadı.')
    })
    return () => {
      cancelled = true
      stopLocalCamera()
    }
  }, [cameraModalOpen])

  const openCameraModal = () => {
    if (disabled) return
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
    setCameraClosing(false)
    setCameraModalOpen(true)
    onCommand('camera')
  }

  const closeCameraModal = () => {
    if (cameraClosing) return
    setCameraClosing(true)
    onCommand('camera')
    closeTimerRef.current = window.setTimeout(() => {
      setCameraModalOpen(false)
      setCameraClosing(false)
      closeTimerRef.current = null
    }, 280)
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && cameraModalOpen && !cameraClosing) closeCameraModal()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [cameraModalOpen, cameraClosing])

  useEffect(() => () => {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
    stopLocalCamera()
  }, [])

  const labels: Record<ControlCommand, string> = {
    shutdown: 'SHUTDOWN',
    pause: paused ? 'DAVAM' : 'FASILƏ',
    camera: cameraActive ? 'KAMERA (✅)' : 'KAMERA (❌)',
    microphone: microphoneMuted ? 'MİKROFON (❌)' : 'MİKROFON (✅)',
  }

  return (
    <>
      <section className="panel control-panel">
        <div className="panel-heading"><span>EVA NƏZARƏT PANELİ</span></div>
        <div className="control-grid">
          {controls.map(({ command, icon, tone }) => {
            const active = (command === 'pause' && paused) || (command === 'camera' && cameraActive) || (command === 'microphone' && !microphoneMuted)
            return (
              <button
                className={`control-button control-button-${tone} ${active ? 'is-active' : ''}`}
                key={command}
                type="button"
                aria-label={labels[command]}
                aria-pressed={command === 'shutdown' ? undefined : active}
                disabled={disabled}
                onClick={command === 'camera' ? openCameraModal : () => onCommand(command)}
              >
                <FontAwesomeIcon icon={command === 'pause' ? (paused ? faPlay : faPause) : icon} aria-hidden="true" />
                <span>{labels[command]}</span>
              </button>
            )
          })}
        </div>
      </section>

      {cameraModalOpen && (
        <div className={`camera-modal-backdrop ${cameraClosing ? 'camera-modal-closing' : ''}`} role="dialog" aria-modal="true" aria-label="EVA kamera görüntüsü" onMouseDown={(event) => { if (event.target === event.currentTarget) closeCameraModal() }}>
          <div className="camera-modal">
            <div className="camera-modal-header">
              <div><span className="camera-modal-eyebrow">E.V.A / VISUAL SENSOR</span><strong>KAMERA</strong></div>
              <button className="camera-modal-close" type="button" aria-label="Kameranı bağla" onClick={closeCameraModal}><FontAwesomeIcon icon={faXmark} /></button>
            </div>
            <div className="camera-viewport">
              <video ref={videoRef} className="camera-video" autoPlay playsInline muted />
              <div className="camera-scanline" />
              <span className="camera-corner camera-corner-tl" /><span className="camera-corner camera-corner-tr" />
              <span className="camera-corner camera-corner-bl" /><span className="camera-corner camera-corner-br" />
              {cameraError && <div className="camera-error">{cameraError}</div>}
            </div>
            <div className="camera-modal-footer"><span><i /> CANLI GÖRÜNTÜ</span><small>ESC / BAĞLA</small></div>
          </div>
        </div>
      )}
    </>
  )
}

export type { ControlCommand }