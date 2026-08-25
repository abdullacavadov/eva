export type EvaState =
  | 'IDLE'
  | 'LISTENING'
  | 'THINKING'
  | 'EXECUTING'
  | 'WAITING_CONFIRMATION'
  | 'SUCCESS'
  | 'ERROR'

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

export interface EvaEvent {
  type: 'state.changed' | 'conversation.user' | 'conversation.assistant' | 'activity.created' | 'context.updated'
  state?: EvaState
  text?: string
  activity?: ActivityItem
  context?: EvaContext
}
