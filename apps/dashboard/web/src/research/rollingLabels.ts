export interface RollingLabelInput {
  foldId: number;
  startDate?: string | null;
  endDate?: string | null;
}

export function rollingSummaryLabel(item: RollingLabelInput): string {
  if (item.startDate && item.endDate) return `${item.startDate} → ${item.endDate}`;
  if (item.startDate) return item.startDate;
  return `窗口 ${item.foldId + 1}`;
}
