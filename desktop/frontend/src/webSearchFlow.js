export async function prepareWebSearchRequest({
  enabled,
  prompt,
  planSearch,
  approvePlan,
  reviewPlan,
}) {
  if (!enabled) {
    return {web_search: false, web_search_plan_id: ''};
  }

  const plan = await planSearch(prompt);
  if (plan.decision === 'allow') {
    return {web_search: true, web_search_plan_id: plan.plan_id};
  }

  const choice = await reviewPlan(plan);
  if (choice === 'local') {
    return {web_search: false, web_search_plan_id: ''};
  }
  if (choice !== 'search' || plan.decision === 'block') {
    return null;
  }

  await approvePlan(plan.plan_id);
  return {web_search: true, web_search_plan_id: plan.plan_id};
}
