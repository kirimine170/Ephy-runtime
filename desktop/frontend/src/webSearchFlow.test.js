import test from 'node:test';
import assert from 'node:assert/strict';

import {prepareWebSearchRequest} from './webSearchFlow.js';


test('disabled web search performs no external planning', async () => {
  let calls = 0;
  const result = await prepareWebSearchRequest({
    enabled: false,
    prompt: 'private prompt',
    planSearch: async () => { calls += 1; },
    approvePlan: async () => { calls += 1; },
    reviewPlan: async () => { calls += 1; },
  });

  assert.deepEqual(result, {web_search: false, web_search_plan_id: ''});
  assert.equal(calls, 0);
});


test('allowed plan searches without approval dialog', async () => {
  let approved = false;
  let reviewed = false;
  const result = await prepareWebSearchRequest({
    enabled: true,
    prompt: 'latest Python release',
    planSearch: async () => ({decision: 'allow', plan_id: 'safe-plan'}),
    approvePlan: async () => { approved = true; },
    reviewPlan: async () => { reviewed = true; },
  });

  assert.deepEqual(result, {web_search: true, web_search_plan_id: 'safe-plan'});
  assert.equal(approved, false);
  assert.equal(reviewed, false);
});


test('confirmed plan requires explicit approval', async () => {
  const approved = [];
  const result = await prepareWebSearchRequest({
    enabled: true,
    prompt: 'contact alice@example.com',
    planSearch: async () => ({decision: 'confirm', plan_id: 'review-plan'}),
    approvePlan: async (planId) => { approved.push(planId); },
    reviewPlan: async () => 'search',
  });

  assert.deepEqual(result, {web_search: true, web_search_plan_id: 'review-plan'});
  assert.deepEqual(approved, ['review-plan']);
});


test('blocked plan can continue locally but cannot be approved', async () => {
  let approved = false;
  const result = await prepareWebSearchRequest({
    enabled: true,
    prompt: 'password=secret-value',
    planSearch: async () => ({decision: 'block', plan_id: 'blocked-plan'}),
    approvePlan: async () => { approved = true; },
    reviewPlan: async () => 'local',
  });

  assert.deepEqual(result, {web_search: false, web_search_plan_id: ''});
  assert.equal(approved, false);
});
