import type { ActivityItem, VictorContext, VictorEvent, VictorState } from '../types/victor.ts'

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const activity = (text: string, kind: ActivityItem['kind'], detail?: string): ActivityItem => ({
  id: crypto.randomUUID(),
  time: new Date().toLocaleTimeString('az-AZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  text,
  kind,
  detail,
})

export async function* demoConversation(): AsyncGenerator<VictorEvent> {
  const context: VictorContext = {
    source: 'Google Calendar',
    title: 'Aktiv kontekst',
    items: [
      { id: 'calendar-1', title: 'Layihə görüşü', subtitle: '26 Avq · 10:00', source: 'Təqvim' },
      { id: 'calendar-2', title: 'İdman zalı', subtitle: '26 Avq · 18:00', source: 'Təqvim' },
      { id: 'calendar-3', title: 'Müştəri zəngi', subtitle: '26 Avq · 14:30', source: 'Təqvim' },
    ],
  }

  const emitState = (state: VictorState): VictorEvent => ({ type: 'state.changed', state })

  yield emitState('LISTENING')
  await wait(700)
  yield { type: 'conversation.user', text: 'Sabah üçün təqvimdə nə var?' }
  yield { type: 'activity.created', activity: activity('İstifadəçi komandası qəbul edildi', 'user', 'Təqvim sorğusu') }
  await wait(500)
  yield emitState('THINKING')
  yield { type: 'activity.created', activity: activity('Təqvim konteksti müəyyənləşdirilir', 'action') }
  await wait(700)
  yield { type: 'context.updated', context }
  yield emitState('EXECUTING')
  yield { type: 'activity.created', activity: activity('Təqvim məlumatları hazırdır', 'success', '3 qarşıdakı tədbir') }
  await wait(500)
  yield { type: 'conversation.assistant', text: 'Sabah təqvimində 3 tədbir görünür. İstəsən, onları sıralayıb göstərə bilərəm.' }
  yield emitState('SUCCESS')
  await wait(1000)
  yield emitState('IDLE')
}
