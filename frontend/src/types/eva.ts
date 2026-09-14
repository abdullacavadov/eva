export type VictorState =
  | 'IDLE'
  | 'LISTENING'
  | 'SPEAKING'
  | 'THINKING'
  | 'EXECUTING'
  | 'WAITING_CONFIRMATION'
  | 'SUCCESS'
  | 'MUTED'
  | 'PAUSED'
  | 'ERROR'
  | 'INITIALISING'

export type ActivityKind = 'system' | 'user' | 'assistant' | 'action' | 'success' | 'error'

export interface ActivityItem {
  id: string
  time: string
  text: string
  kind: ActivityKind
  detail?: string
}

export interface ContextItem {
  id: string
  title: string
  subtitle?: string
  source?: string
  selected?: boolean
}

export interface VictorContext {
  source?: string
  title?: string
  items: ContextItem[]
}

export type VictorControlState = {
  paused?: boolean
  camera_active?: boolean
  microphone_muted?: boolean
}

export interface MediaProductionScene {
  index: number
  asset?: string
  text?: string
  visual_prompt?: string
  duration?: number
  generated?: boolean
}

export interface MediaProductionEvent {
  job_id: string
  status: 'running' | 'completed' | 'failed'
  stage?: string
  progress?: number
  message?: string
  transcript?: string
  scenes?: MediaProductionScene[]
  error?: string
  provider?: string
  model?: string
}

export type VictorEvent =
  | { type: 'connection.ready' }
  | {
      type: 'runtime.snapshot'
      state?: VictorState | null
      messages?: Array<{ type: 'conversation.user' | 'conversation.assistant'; text: string }>
      activities?: ActivityItem[]
      context?: VictorContext | null
      control?: VictorControlState | null
    }
  | { type: 'bridge.error'; message?: string }
  | { type: 'state.changed'; state: VictorState }
  | { type: 'audio.level'; level: number }
  | { type: 'conversation.user'; text: string }
  | { type: 'conversation.assistant'; text: string }
  | { type: 'activity.created'; activity: ActivityItem }
  | { type: 'context.updated'; context: VictorContext }
  | { type: 'control.state'; control: VictorControlState }
  | { type: 'webcam.frame'; data: string }
  | { type: 'tool.started'; tool: string; args?: Record<string, unknown> }
  | { type: 'tool.completed'; tool: string; success: boolean; result?: string }
  | { type: 'media.production'; data: MediaProductionEvent }

// Geriyə uyğunluq: wire/protokol və mövcud komponentlər mərhələli şəkildə Victor adlarına keçirilə bilər.
export type EvaState = VictorState
export type EvaContext = VictorContext
export type EvaControlState = VictorControlState
export type EvaEvent = VictorEvent
