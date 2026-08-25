import type { ActivityItem, EvaContext, EvaEvent, EvaState } from '../types/eva'

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const activity = (text: string, kind: ActivityItem['kind'], detail?: string): ActivityItem => ({
  id: crypto.randomUUID(),
  time: new Date().toLocaleTimeString('az-AZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  text,
  kind,
  detail,
})

export async function* demoConversation(): AsyncGenerator<EvaEvent> {
  const context: EvaContext = {
    source: 'Google Calendar',
    title: 'Active context',
    items: [
      { id: 'calendar-1', title: 'Project Meeting', subtitle: '24 Aug · 10:00', source: 'Calendar' },
      { id: 'calendar-2', title: 'Gym', subtitle: '24 Aug · 18:00', source: 'Calendar' },
      { id: 'calendar-3', title: 'Client Call', subtitle: '25 Aug · 14:30', source: 'Calendar' },
    ],
  }

  const emitState = (state: EvaState): EvaEvent => ({ type: 'state.changed', state })

  yield emitState('LISTENING')
  await wait(700)
  yield { type: 'conversation.user', text: 'Sabah üçün təqvimdə nə var?' }
  yield { type: 'activity.created', activity: activity('User command received', 'user', 'Calendar query') }
  await wait(500)
  yield emitState('THINKING')
  yield { type: 'activity.created', activity: activity('Resolving calendar context', 'action') }
  await wait(700)
  yield { type: 'context.updated', context }
  yield emitState('EXECUTING')
  yield { type: 'activity.created', activity: activity('Calendar data ready', 'success', '3 upcoming events') }
  await wait(500)
  yield { type: 'conversation.assistant', text: 'Sabah təqvimində 3 tədbir görünür. İstəsən, onları sıralayıb göstərə bilərəm.' }
  yield emitState('SUCCESS')
  await wait(1000)
  yield emitState('IDLE')
}
