# Gantt Chart Optimization Design

**Date**: 2026-05-07
**Status**: Approved

## Goal

Optimize the frontend Gantt chart to match the visual style of `GANTE.py` reference implementation, while ensuring correct parallel task display based on backend `parallel_batches` data.

## Reference

- **GANTE.py**: `G:\学习\课题组\知识图谱\论文\大修\GanTe\GANTE.py`
- **Key Features**:
  - Human tasks: Blue (#4C72B0)
  - Robot tasks: Orange (#DD8452)
  - Time axis in minutes
  - Parallel tasks (bracketed `[...]`) start at same time, duration = max of group

## Design

### 1. Type Changes (`frontend/src/types/index.ts`)

Add `ParallelBatch` interface:

```typescript
export interface ParallelBatch {
  batch_id: number
  tasks: number[]
  start_time: number  // seconds
  duration: number    // seconds
}
```

### 2. Frontend Components to Modify

#### 2.1 SequencePlanner.tsx (Line ~414)

Pass `parallelBatches` to GanttChart:

```tsx
<GanttChart
  steps={result.data.steps}
  parallelBatches={result.data.parallel_batches || []}
/>
```

#### 2.2 GanttChart.tsx

**New Props**:
```typescript
interface GanttChartProps {
  steps: DisassemblyStep[]
  parallelBatches?: ParallelBatch[]
}
```

**Key Logic**:
1. Build `stepId → batch` mapping from `parallelBatches`
2. Same-batch tasks share same `start_time`, bars left-align
3. Time axis in minutes (divide by 60)
4. Color scheme: human=#4C72B0, robot=#DD8452

#### 2.3 index.css

Update color variables:

```css
.gantt-bar.human {
  background: #4C72B0;
}
.gantt-bar.robot {
  background: #DD8452;
}
```

## Backend (No Changes)

- `src/graphrag/planner.py`: `compute_parallel_batches()` already correct
- API returns `parallel_batches` in response

## Visual Comparison

| Feature | Current | After |
|---------|---------|-------|
| Human color | #6b7280 (gray) | #4C72B0 (blue) |
| Robot color | #2563eb (blue) | #DD8452 (orange) |
| Time axis | seconds | minutes |
| Parallel tasks | not recognized | left-aligned |
| Bar width | fixed percentage | proportional to duration |

## Implementation Steps

1. Update `frontend/src/types/index.ts` - add `ParallelBatch` type
2. Update `SequencePlanner.tsx` - pass `parallelBatches` prop
3. Update `GanttChart.tsx` - add parallel logic, time conversion, colors
4. Update `frontend/src/index.css` - update color variables
5. Test and verify

## Verification

- [ ] API returns `parallel_batches` correctly
- [ ] Frontend receives and parses `parallel_batches`
- [ ] Parallel task bars are left-aligned
- [ ] Colors match GANTE.py style
- [ ] Time axis shows minutes