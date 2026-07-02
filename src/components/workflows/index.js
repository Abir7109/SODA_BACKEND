import { lazy } from 'react'

const WorkflowOutside = lazy(() => import('./WorkflowOutside'))
const WorkflowProjectReview = lazy(() => import('./WorkflowProjectReview'))
const WorkflowBreakTime = lazy(() => import('./WorkflowBreakTime'))
const WorkbaseShowcase = lazy(() => import('./WorkbaseShowcase'))
import WorkflowMemoryView from './WorkflowMemoryView'
import WorkflowNewsBriefing from './WorkflowNewsBriefing'
const WorkflowIELTSSpeaking = lazy(() => import('./WorkflowIELTSSpeaking'))
const WorkflowIELTSMock = lazy(() => import('./WorkflowIELTSMock'))
const WorkflowPentestScan = lazy(() => import('./WorkflowPentestScan'))
const WorkflowReminder = lazy(() => import('./WorkflowReminder'))

export const WORKFLOW_MAP = {
  outside: WorkflowOutside,
  'project-review': WorkflowProjectReview,
  'break-time': WorkflowBreakTime,
  'memory-view': WorkflowMemoryView,
  'news-briefing': WorkflowNewsBriefing,
  'workbase-showcase': WorkbaseShowcase,
  'ielts-speaking': WorkflowIELTSSpeaking,
  'ielts-mock': WorkflowIELTSMock,
  'pentest-scan': WorkflowPentestScan,
  'reminder': WorkflowReminder,
}

export function getWorkflowComponent(name) {
  return WORKFLOW_MAP[name] || null
}
