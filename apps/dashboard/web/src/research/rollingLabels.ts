export interface RollingLabelInput {
  foldId: number;
  startDate?: string | null;
  endDate?: string | null;
  calendar?: {
    mode: 'exact' | 'range' | 'unknown';
    startDate?: string;
    endDate?: string;
    startDateMin?: string;
    endDateMax?: string;
  };
}

export function rollingSummaryLabel(item: RollingLabelInput): string {
  if (item.startDate && item.endDate) return `${item.startDate} → ${item.endDate}`;
  if (item.calendar?.mode === 'exact' && item.calendar.startDate && item.calendar.endDate) {
    return `${item.calendar.startDate} → ${item.calendar.endDate}`;
  }
  if (item.calendar?.mode === 'range' && item.calendar.startDateMin && item.calendar.endDateMax) {
    return `${item.calendar.startDateMin} → ${item.calendar.endDateMax}（个股日期范围）`;
  }
  if (item.startDate) return item.startDate;
  return `窗口 ${item.foldId + 1}`;
}
