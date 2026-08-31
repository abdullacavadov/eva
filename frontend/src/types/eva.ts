export type EvaState =
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

export interface EvaContext {
  source?: string
  title?: string
  items: ContextItem[]
}

export type EvaControlState = {
  paused?: boolean
  camera_active?: boolean
  microphone_muted?: boolean
}

export type EvaEvent =
  | { type: 'connection.ready' }
  | {
      type: 'runtime.snapshot'
      state?: EvaState | null
      messages?: Array<{ type: 'conversation.user' | 'conversation.assistant'; text: string }>
      activities?: ActivityItem[]
      context?: EvaContext | null
      control?: EvaControlState | null
    }
  | { type: 'bridge.error'; message?: string }
  | { type: 'state.changed'; state: EvaState }
  | { type: 'conversation.user'; text: string }
  | { type: 'conversation.assistant'; text: string }
  | { type: 'activity.created'; activity: ActivityItem }
  | { type: 'context.updated'; context: EvaContext }
  | { type: 'control.state'; control: EvaControlState }
  | { type: 'webcam.frame'; data: string }
  | { type: 'tool.started'; tool: string; args?: Record<string, unknown> }
  | { type: 'tool.completed'; tool: string; success: boolean; result?: string }
