import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync(
  new URL('./components/ContextualResearchPanel.tsx', import.meta.url),
  'utf8',
);

test('contextual research panel exposes factual research sections', () => {
  assert.match(source, /20日背景/);
  assert.match(source, /日型/);
  assert.match(source, /参考价位/);
  assert.match(source, /Session 分箱/);
  assert.match(source, /Setup 事件/);
  assert.match(source, /跨市场确认/);
  assert.doesNotMatch(source, /Confluence Score|ICT Score|汇合评分/);
});

test('contextual research panel renders event studies only from supplied data', () => {
  assert.match(source, /事件研究/);
  assert.match(source, /eventStudies/);
});

test('contextual research panel exposes checklist and conditional history statistics', () => {
  assert.match(source, /条件清单/);
  assert.match(source, /历史条件统计/);
  assert.match(source, /conditionalResearch/);
  assert.match(source, /sampleCount/);
  assert.match(source, /expectancy/);
  assert.doesNotMatch(source, /Confluence Score|ICT Score|汇合评分/);
});
