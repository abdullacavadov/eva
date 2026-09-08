import { useEffect, useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFilm, faXmark, faCheck, faSpinner, faTriangleExclamation, faImage, faMicrophone, faMusic, faLayerGroup, faWandMagicSparkles } from '@fortawesome/free-solid-svg-icons'
import type { MediaProductionEvent } from '../types/eva'
import '../styles/media-production.css'

const STAGES = [
  'transcribing',
  'planning_scenes',
  'analyzing_assets',
  'selecting_assets',
  'generating_missing_images',
  'generating_video',
  'generating_voice',
  'generating_music',
  'rendering',
  'validating',
  'completed',
]

const stageLabels: Record<string, string> = {
  queued: 'Növbəyə alındı',
  transcribing: 'Transkripsiya / ssenari',
  transcript_ready: 'Transkripsiya hazırdır',
  planning_scenes: 'Səhnələr müəyyənləşdirilir',
  scenes_ready: 'Səhnələr hazırdır',
  analyzing_assets: 'Lokal şəkillər analiz edilir',
  selecting_assets: 'Uyğun şəkillər seçilir',
  generating_missing_images: 'Çatışmayan şəkillər yaradılır',
  generating_video: 'AI video səhnələri yaradılır',
  generating_voice: 'Narrasiya hazırlanır',
  generating_music: 'Musiqi hazırlanır',
  rendering: 'Final video render edilir',
  validating: 'Video yoxlanılır',
  completed: 'Tamamlandı',
  failed: 'Xəta baş verdi',
}

function stageIcon(stage: string) {
  if (stage.includes('image') || stage.includes('asset')) return faImage
  if (stage.includes('voice') || stage.includes('transcrib')) return faMicrophone
  if (stage.includes('music')) return faMusic
  if (stage.includes('video') || stage.includes('render')) return faFilm
  return faLayerGroup
}

export function MediaProductionPanel() {
  const [event, setEvent] = useState<MediaProductionEvent | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handler = (customEvent: Event) => {
      const detail = (customEvent as CustomEvent<MediaProductionEvent>).detail
      if (!detail?.job_id) return
      setEvent((current) => ({ ...current, ...detail }))
      if (detail.status === 'running') setOpen(true)
    }
    window.addEventListener('eva:media-production', handler)
    return () => window.removeEventListener('eva:media-production', handler)
  }, [])

  const visibleStages = useMemo(() => {
    if (!event) return []
    const current = event.stage || 'queued'
    const index = STAGES.indexOf(current)
    return STAGES.map((stage, stageIndex) => ({
      stage,
      state: stage === current ? 'current' : stageIndex < index ? 'done' : 'pending',
    }))
  }, [event])

  if (!event || event.status === 'completed') return null

  const progress = Math.max(0, Math.min(100, Number(event.progress ?? 0)))
  const failed = event.status === 'failed'

  return (
    <>
      <button className="media-production-trigger" onClick={() => setOpen(true)} title="Video prodakşn prosesini göstər">
        <FontAwesomeIcon icon={faFilm} />
        <span>VİDEO {failed ? 'XƏTASI' : 'HAZIRLANIR'}</span>
        <strong>{progress}%</strong>
      </button>

      {open && (
        <div className="media-production-backdrop" onClick={() => setOpen(false)}>
          <section className="media-production-panel" onClick={(e) => e.stopPropagation()}>
            <header>
              <div>
                <span className="media-production-kicker">E.V.A / MEDIA PIPELINE</span>
                <h2><FontAwesomeIcon icon={faFilm} /> Video prodakşnı</h2>
              </div>
              <button className="media-production-close" onClick={() => setOpen(false)} aria-label="Bağla">
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </header>

            <div className="media-production-progress">
              <div className="media-production-progress-head">
                <span>{stageLabels[event.stage || 'queued'] || event.stage}</span>
                <strong>{progress}%</strong>
              </div>
              <div className="media-production-progress-track"><i style={{ width: `${progress}%` }} /></div>
              <p>{event.message || 'İş davam edir...'}</p>
            </div>

            {event.transcript && (
              <article className="media-production-card media-production-transcript">
                <div className="media-production-card-title"><FontAwesomeIcon icon={faMicrophone} /> TRANSKRİPSİYA / NARRASİYA</div>
                <p>{event.transcript}</p>
              </article>
            )}

            {event.scenes?.length ? (
              <article className="media-production-card">
                <div className="media-production-card-title"><FontAwesomeIcon icon={faLayerGroup} /> SƏHNƏLƏR</div>
                <div className="media-production-scenes">
                  {event.scenes.map((scene) => (
                    <div className="media-production-scene" key={scene.index}>
                      <span>#{String(scene.index + 1).padStart(2, '0')}</span>
                      <div>
                        <strong>{scene.text || scene.visual_prompt || 'Vizual səhnə'}</strong>
                        <small>{scene.asset || 'GENERATE'} · {scene.duration ?? '—'} san</small>
                      </div>
                      {scene.generated ? <FontAwesomeIcon icon={faWandMagicSparkles} /> : <FontAwesomeIcon icon={faCheck} />}
                    </div>
                  ))}
                </div>
              </article>
            ) : null}

            <div className="media-production-stage-list">
              {visibleStages.map(({ stage, state }) => (
                <div className={`media-production-stage ${state}`} key={stage}>
                  <span className="media-production-stage-icon">
                    {state === 'done' ? <FontAwesomeIcon icon={faCheck} /> : state === 'current' ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={stageIcon(stage)} />}
                  </span>
                  <span>{stageLabels[stage]}</span>
                </div>
              ))}
            </div>

            {failed && event.error && (
              <div className="media-production-error">
                <FontAwesomeIcon icon={faTriangleExclamation} />
                <div><strong>Xəta</strong><span>{event.error}</span></div>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  )
}
