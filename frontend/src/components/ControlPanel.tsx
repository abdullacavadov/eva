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
  cameraPreview?: string | null
  disabled?: boolean
}

const controls = [
  { command: 'shutdown' as const, label: 'SÖNDÜR', icon: faPowerOff, tone: 'danger' },
  { command: 'pause' as const, label: 'FASİLƏ', icon: faPause, tone: 'warning' },
  { command: 'camera' as const, label: 'KAMERA', icon: faCamera, tone: 'camera' },
  { command: 'microphone' as const, label: 'MİKRAFON', icon: faMicrophone, tone: 'microphone' },
]

export function ControlPanel({ onCommand, paused, cameraActive, microphoneMuted, cameraPreview = null, disabled = false }: ControlPanelProps) {
  const [cameraModalOpen, setCameraModalOpen] = useState(false)
  const [cameraClosing, setCameraClosing] = useState(false)
  const [preview, setPreview] = useState<string | null>(cameraPreview)
  const closeTimerRef = useRef<number | null>(null)

  useEffect(() => {
    setPreview(cameraPreview ?? null)
  }, [cameraPreview])

  useEffect(() => {
    const handleWebcamFrame = (event: Event) => {
      const frame = (event as CustomEvent<string>).detail
      if (typeof frame === 'string' && frame) setPreview(frame)
    }
    window.addEventListener('eva:webcam-frame', handleWebcamFrame)
    return () => window.removeEventListener('eva:webcam-frame', handleWebcamFrame)
  }, [])

  const finishClose = () => {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
    setCameraModalOpen(false)
    setCameraClosing(false)
    closeTimerRef.current = null
  }

  const startCloseAnimation = () => {
    if (!cameraModalOpen || cameraClosing) return
    setCameraClosing(true)
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
    closeTimerRef.current = window.setTimeout(finishClose, 280)
  }

  useEffect(() => {
    if (cameraActive) {
      if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
      setCameraClosing(false)
      setCameraModalOpen(true)
      return
    }
    startCloseAnimation()
  }, [cameraActive])

  useEffect(() => () => {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
  }, [])

  const toggleCamera = () => {
    if (disabled) return
    onCommand('camera')
  }

  const closeCameraModal = () => {
    if (cameraClosing) return
    startCloseAnimation()
    if (cameraActive) onCommand('camera')
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && cameraModalOpen && !cameraClosing) closeCameraModal()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [cameraModalOpen, cameraClosing, cameraActive])

  const labels: Record<ControlCommand, string> = {
    shutdown: 'SHUTDOWN',
    pause: paused ? 'DAVAM' : 'FASILƏ',
    camera: cameraActive ? 'KAMERA (AÇIQ)' : 'KAMERA (BAĞLI)',
    microphone: microphoneMuted ? 'MİKRAFON (SƏSSİZ)' : 'MİKRAFON (AÇIQ)',
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
                onClick={command === 'camera' ? toggleCamera : () => onCommand(command)}
              >
                <FontAwesomeIcon icon={command === 'pause' ? (paused ? faPlay : faPause) : icon} aria-hidden="true" />
                <span>{labels[command]}</span>
              </button>
            )
          })}
        </div>
      </section>

      {cameraModalOpen && (
        <div
          className={`camera-modal-backdrop ${cameraClosing ? 'camera-modal-closing' : ''}`}
          role="dialog"
          aria-modal="true"
          aria-label="EVA kamera görüntüsü"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeCameraModal()
          }}
        >
          <div className="camera-modal">
            <div className="camera-modal-header">
              <div><span className="camera-modal-eyebrow">E.V.A / VISUAL SENSOR</span><strong>KAMERA</strong></div>
              <button className="camera-modal-close" type="button" aria-label="Kameranı bağla" onClick={closeCameraModal}><FontAwesomeIcon icon={faXmark} /></button>
            </div>
            <div className="camera-viewport">
              {preview ? (
                <img src={preview} className="camera-video" alt="EVA canlı kamera görüntüsü" />
              ) : (
                <div className="camera-error">CANLI GÖRÜNTÜ GÖZLƏNİLİR...</div>
              )}
              <div className="camera-scanline" />
              <span className="camera-corner camera-corner-tl" /><span className="camera-corner camera-corner-tr" />
              <span className="camera-corner camera-corner-bl" /><span className="camera-corner camera-corner-br" />
            </div>
            <div className="camera-modal-footer"><span><i /> CANLI GÖRÜNTÜ</span><small>ESC / BAĞLA</small></div>
          </div>
        </div>
      )}
    </>
  )
}

export type { ControlCommand }