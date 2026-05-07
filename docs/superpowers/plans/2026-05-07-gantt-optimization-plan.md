# Gantt Chart Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize frontend Gantt chart to match GANTE.py visual style with correct parallel task display.

**Architecture:** Frontend-only changes. Backend (`src/graphrag/planner.py`) already correctly computes `parallel_batches`. Frontend needs to receive this data and render parallel tasks with left-aligned bars, GANTE.py colors, and minute-based time axis.

**Tech Stack:** React + TypeScript + CSS

---

## File Structure

```
frontend/src/
├── types/index.ts           # Add ParallelBatch type
├── pages/SequencePlanner.tsx  # Pass parallelBatches to GanttChart
├── components/GanttChart.tsx  # Core rendering logic changes
└── index.css               # Color variable updates
```

---

## Tasks

### Task 1: Add ParallelBatch Type

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add ParallelBatch interface**

Find the `ParallelBatch` interface location (around line 56) and add after it:

```typescript
export interface ParallelBatch {
  batch_id: number
  tasks: number[]
  start_time: number
  duration: number
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): add ParallelBatch type for Gantt chart"
```

---

### Task 2: Pass parallelBatches from SequencePlanner to GanttChart

**Files:**
- Modify: `frontend/src/pages/SequencePlanner.tsx:413-415`

- [ ] **Step 1: Update GanttChart component call**

Find line 414:
```tsx
<GanttChart steps={result.data.steps} />
```

Replace with:
```tsx
<GanttChart
  steps={result.data.steps}
  parallelBatches={result.data.parallel_batches || []}
/>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/SequencePlanner.tsx
git commit -m "feat(frontend): pass parallelBatches to GanttChart"
```

---

### Task 3: Update GanttChart Component

**Files:**
- Modify: `frontend/src/components/GanttChart.tsx`

- [ ] **Step 1: Add ParallelBatch import**

Find the import at top:
```typescript
import { DisassemblyStep } from '../types'
```

Replace with:
```typescript
import { DisassemblyStep, ParallelBatch } from '../types'
```

- [ ] **Step 2: Update GanttChartProps interface**

Find the interface:
```typescript
interface GanttChartProps {
  steps: DisassemblyStep[]
}
```

Replace with:
```typescript
interface GanttChartProps {
  steps: DisassemblyStep[]
  parallelBatches?: ParallelBatch[]
}
```

- [ ] **Step 3: Update component to use parallelBatches**

Find the component function signature:
```typescript
export function GanttChart({ steps }: GanttChartProps) {
```

Replace with:
```typescript
export function GanttChart({ steps, parallelBatches = [] }: GanttChartProps) {
```

- [ ] **Step 4: Build stepId to batch mapping**

Find the line with `const totalTime = ...` (around line 19) and replace everything from there to the return statement with:

```typescript
  // Build stepId -> batch mapping
  const stepToBatch = new Map<number, ParallelBatch>()
  parallelBatches.forEach(batch => {
    batch.tasks.forEach(taskId => {
      stepToBatch.set(taskId, batch)
    })
  })

  // Calculate total time in minutes
  const totalTimeMinutes = parallelBatches.length > 0
    ? Math.max(...parallelBatches.map(b => b.start_time + b.duration)) / 60
    : Math.max(...steps.map(s => (s.start_time || 0) + (s.time_seconds || 0)), 1) / 60

  // Time axis markers in minutes
  const timeMarkers = [0, 1, 2, 3, 4, 5, 6].map(i => ({
    percent: (i / 6) * 100,
    label: Math.round((i / 6) * totalTimeMinutes)
  }))
```

- [ ] **Step 5: Update bar rendering for parallel tasks**

Find the rendering logic inside the map (around line 77-88) and replace:

```tsx
                <div className="gantt-bar-container" style={{ position: 'relative' }}>
                  <div
                    className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'} `}
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      width: `${Math.max(widthPercent, 2)}%`
                    }}
                    title={`${stepName} (${duration}s)`}
                  >
                    {duration}s
                  </div>
                </div>
```

Replace with:
```tsx
                <div className="gantt-bar-container" style={{ position: 'relative' }}>
                  <div
                    className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'}`}
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      width: `${Math.max(widthPercent, 2)}%`
                    }}
                    title={`${stepName} (${durationMinutes.toFixed(2)}min)`}
                  >
                    {durationMinutes.toFixed(2)}m
                  </div>
                </div>
```

- [ ] **Step 6: Update variable calculations for time in minutes**

Find the calculation block inside the map and replace:
```typescript
            const startTime = step.start_time || 0
            const duration = step.time_seconds || 0
            const leftPercent = (startTime / totalTime) * 100
            const widthPercent = (duration / totalTime) * 100
```

Replace with:
```typescript
            const startTimeSeconds = step.start_time || 0
            const durationSeconds = step.duration || step.time_seconds || 0
            const startTimeMinutes = startTimeSeconds / 60
            const durationMinutes = durationSeconds / 60
            const leftPercent = (startTimeMinutes / totalTimeMinutes) * 100
            const widthPercent = (durationMinutes / totalTimeMinutes) * 100
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/GanttChart.tsx
git commit -m "feat(frontend): update GanttChart with parallel batches and minute-based time"
```

---

### Task 4: Update CSS Colors

**Files:**
- Modify: `frontend/src/index.css:129-134`

- [ ] **Step 1: Update gantt-bar.human color**

Find:
```css
.gantt-bar.human {
  background: #6b7280;
}
```

Replace with:
```css
.gantt-bar.human {
  background: #4C72B0;
}
```

- [ ] **Step 2: Update gantt-bar.robot color**

Find:
```css
.gantt-bar.robot {
  background: #2563eb;
}
```

Replace with:
```css
.gantt-bar.robot {
  background: #DD8452;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "style(frontend): update Gantt chart colors to match GANTE.py"
```

---

## Verification Steps

After all tasks complete:

1. Start the backend: `uvicorn src.main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm run dev`
3. Navigate to Sequence Planner page
4. Select a battery model and generate sequence
5. Verify:
   - [ ] Human tasks show as blue (#4C72B0)
   - [ ] Robot tasks show as orange (#DD8452)
   - [ ] Time axis shows minutes (e.g., "1m", "2m")
   - [ ] Parallel tasks have bars left-aligned at same position
   - [ ] Bar widths are proportional to duration

---

## Plan Summary

| Task | Description | Files Modified |
|------|-------------|----------------|
| 1 | Add ParallelBatch type | `frontend/src/types/index.ts` |
| 2 | Pass parallelBatches prop | `frontend/src/pages/SequencePlanner.tsx` |
| 3 | Update GanttChart logic | `frontend/src/components/GanttChart.tsx` |
| 4 | Update CSS colors | `frontend/src/index.css` |