export function renderOverviewPresetRuntimeHintCard({
  presetName,
  runtimeProfile,
  smokeEnabled,
  isCurrent,
  escapeHtml,
}) {
  return `
    <div class="runtime-result-card">
      <div class="runtime-result-head">
        <span class="runtime-result-title">Launcher Runtime</span>
        <span class="runtime-pill ${runtimeProfile.pillClass}">${escapeHtml(runtimeProfile.label)}</span>
      </div>
      <div class="runtime-result-meta">current_runtime=<span class="runtime-pill ${runtimeProfile.matchPillClass}">${escapeHtml(runtimeProfile.matchLabel)}</span></div>
      <div class="runtime-result-text">${escapeHtml(runtimeProfile.validationNote)}</div>
      <div class="runtime-result-meta">preset=${escapeHtml(presetName || '-')} | smoke=${escapeHtml(smokeEnabled ? 'enabled' : 'disabled')}</div>
      <div class="actions">
        ${
          isCurrent
            ? '<button class="ghost-btn overview-open-runtime-btn">Open Runtime Controls</button>'
            : `
              <button class="ghost-btn overview-apply-runtime-profile-btn" data-preset-name="${escapeHtml(presetName || '')}">Apply Runtime Profile</button>
              <button class="primary-btn overview-apply-runtime-stack-btn" data-preset-name="${escapeHtml(presetName || '')}">Apply Runtime + Start Stack</button>
            `
        }
      </div>
    </div>
  `;
}

export function renderSelectedPresetPreviewCard({
  preset,
  watchPathsSummary,
  ingestPathsSummary,
  runtimeProfileDescription,
  runtimeMatch,
  smokePolicy,
  batchSelectionMeta,
  primaryActionsHtml,
  batchSelectionButtonsHtml,
  singlePresetBatchActionsHtml,
  workflowShortcutButtonsHtml,
  verificationButtonHtml,
  loadRequestButtonsHtml,
  escapeHtml,
}) {
  return `
    <div class="runtime-result-card">
      <div class="runtime-result-head">
        <span class="runtime-result-title">${escapeHtml(preset.name || '-')}</span>
        <span class="runtime-pill ${preset.workflow_run_smoke ? 'neutral' : 'optional'}">${escapeHtml(preset.workflow_run_smoke ? 'smoke' : 'no smoke')}</span>
      </div>
      <div class="runtime-summary-grid">
        <div class="runtime-summary-card">
          <div class="runtime-summary-title">Watch Scope</div>
          <div class="runtime-result-text">${escapeHtml(preset.watch_project || '(default)')}</div>
          <div class="runtime-result-meta">${escapeHtml(watchPathsSummary)}</div>
        </div>
        <div class="runtime-summary-card">
          <div class="runtime-summary-title">Ingest Scope</div>
          <div class="runtime-result-text">${escapeHtml(preset.ingest_project || '(default)')}</div>
          <div class="runtime-result-meta">${escapeHtml(ingestPathsSummary)}</div>
        </div>
        <div class="runtime-summary-card">
          <div class="runtime-summary-title">RAG Scope</div>
          <div class="runtime-result-text">project=${escapeHtml(preset.rag_project || '(default)')}</div>
          <div class="runtime-result-meta">source=${escapeHtml(preset.rag_source_path || '-')} | top_k=${escapeHtml(String(preset.rag_top_k || 5))}</div>
        </div>
        <div class="runtime-summary-card">
          <div class="runtime-summary-title">Eval Scope</div>
          <div class="runtime-result-text">project=${escapeHtml(preset.eval_project || '(default)')}</div>
          <div class="runtime-result-meta">source=${escapeHtml(preset.eval_source_path || '-')} | top_k=${escapeHtml(String(preset.eval_top_k || 5))}</div>
        </div>
      </div>
      <div class="runtime-result-meta">dataset=${escapeHtml(preset.eval_dataset || 'configs/eval.sample.yaml')} | with_answer=${escapeHtml(preset.eval_with_answer ? 'true' : 'false')}</div>
      <div class="runtime-result-meta">runtime_profile=${escapeHtml(runtimeProfileDescription)} | current_runtime=<span class="runtime-pill ${runtimeMatch.matchPillClass}">${escapeHtml(runtimeMatch.matchLabel)}</span></div>
      <div class="runtime-result-meta">${escapeHtml(smokePolicy)}</div>
      <div class="runtime-result-meta">representative_chat=${escapeHtml(preset.chat_request_name || '-')} | ingest=${escapeHtml(preset.ingest_request_name || '-')}</div>
      <div class="runtime-result-meta">representative_rag=${escapeHtml(preset.rag_request_name || '-')} | eval=${escapeHtml(preset.eval_request_name || '-')}</div>
      <div class="runtime-result-meta">chat_expect=${escapeHtml(preset.chat_expect_contains || '-')} | rag_expect=${escapeHtml(preset.rag_expect_contains || '-')}</div>
      <div class="runtime-result-meta">eval_min_source_hit_rate=${escapeHtml(String(preset.eval_min_source_hit_rate || 0))}</div>
      <div class="runtime-result-meta">${batchSelectionMeta}</div>
      <div class="actions">
        ${primaryActionsHtml}
        ${batchSelectionButtonsHtml}
        ${singlePresetBatchActionsHtml}
        ${workflowShortcutButtonsHtml}
        ${verificationButtonHtml}
        ${loadRequestButtonsHtml}
      </div>
    </div>
  `;
}

export function renderSelectedPresetWorkflowEmptyCard({
  presetName,
  runtimeProfileDescription,
  runtimeMatch,
  issuesText,
  batchSelectionMeta,
  actionsHtml,
  escapeHtml,
}) {
  return `
    <div class="runtime-result-card">
      <div class="runtime-result-head">
        <span class="runtime-result-title">${escapeHtml(presetName)}</span>
        <span class="runtime-pill neutral">no runs</span>
      </div>
      <div class="runtime-result-meta">runtime_profile=${escapeHtml(runtimeProfileDescription)}</div>
      <div class="runtime-result-meta">current_runtime=<span class="runtime-pill ${runtimeMatch.matchPillClass}">${escapeHtml(runtimeMatch.matchLabel)}</span></div>
      <div class="runtime-result-text">This preset has no workflow history yet.</div>
      <div class="runtime-result-meta">validation_issues=${escapeHtml(issuesText)}</div>
      <div class="runtime-result-meta">${batchSelectionMeta}</div>
      <div class="actions">
        ${actionsHtml}
      </div>
    </div>
  `;
}

export function renderPresetCatalogCard({
  preset,
  selectedInBatch,
  validationMetaHtml,
  smokePolicy,
  latestHistoryHtml,
  expandedScopeHtml,
  singlePresetBatchActionsHtml,
  workflowShortcutButtonsHtml,
  runtimeActionsHtml,
  verificationDisabled,
  retryDisabled,
  expanded,
  escapeHtml,
}) {
  return `
    <div class="runtime-result-card">
      <div class="runtime-result-head">
        <span class="runtime-result-title">
          <label class="check-field inline">
            <input class="batch-preset-checkbox" type="checkbox" data-preset-name="${escapeHtml(preset.name || '')}" ${selectedInBatch ? 'checked' : ''} />
            ${escapeHtml(preset.name || '-')}
          </label>
        </span>
        <span class="runtime-pill ${preset.workflow_run_smoke ? 'neutral' : 'optional'}">${escapeHtml(preset.workflow_run_smoke ? 'smoke' : 'no smoke')}</span>
      </div>
      ${validationMetaHtml}
      <div class="runtime-result-meta">${escapeHtml(smokePolicy)}</div>
      <div class="runtime-result-text">watch=${escapeHtml(preset.watch_project || '-')} | ingest=${escapeHtml(preset.ingest_project || '-')} | eval=${escapeHtml(preset.eval_project || '-')}</div>
      <div class="runtime-result-meta">rag_source=${escapeHtml(preset.rag_source_path || '-')} | eval_source=${escapeHtml(preset.eval_source_path || '-')}</div>
      <div class="runtime-result-meta">eval_dataset=${escapeHtml(preset.eval_dataset || 'configs/eval.sample.yaml')} | eval_top_k=${escapeHtml(String(preset.eval_top_k || 5))}</div>
      ${latestHistoryHtml}
      ${expandedScopeHtml}
      <div class="actions">
        <button class="ghost-btn toggle-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}">${expanded ? 'Collapse' : 'Expand'}</button>
        <button class="ghost-btn show-preset-workflow-card-btn" data-preset-name="${escapeHtml(preset.name || '')}">View Latest Workflow</button>
        <button class="ghost-btn load-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}">Load</button>
        ${singlePresetBatchActionsHtml}
        ${workflowShortcutButtonsHtml}
        ${runtimeActionsHtml}
        <button class="ghost-btn validate-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}">Validate</button>
        <button class="ghost-btn verify-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}" ${verificationDisabled ? 'disabled' : ''}>Run Verification</button>
        <button class="ghost-btn export-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}">Export Summary</button>
        <button class="ghost-btn retry-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}" ${retryDisabled ? 'disabled' : ''}>Retry Last</button>
        <button class="ghost-btn run-preset-card-btn" data-preset-name="${escapeHtml(preset.name || '')}">Run Stack + Ingest + Eval</button>
      </div>
    </div>
  `;
}

export function renderSelectedPresetWorkflowVerificationSection({
  latestVerification,
  latestVerificationSummary,
  representativeStepItemsHtml,
  escapeHtml,
}) {
  if (!latestVerification) {
    return '';
  }

  return `
    <div class="runtime-result-item">
      <div class="runtime-result-head">
        <span class="runtime-result-name">Latest Verification Snapshot</span>
        <span class="runtime-pill ${latestVerification.item.status === 'ok' ? 'optional' : latestVerification.item.status === 'error' ? 'required' : 'neutral'}">${escapeHtml(latestVerification.item.status || '-')}</span>
      </div>
      <div class="runtime-result-meta">timestamp=${escapeHtml(latestVerification.item.timestamp || '-')} | representative_runs=${escapeHtml(String(latestVerificationSummary.total))}</div>
      <div class="runtime-result-meta">ok=${escapeHtml(String(latestVerificationSummary.okCount))} | failed=${escapeHtml(String(latestVerificationSummary.failedCount))} | skipped=${escapeHtml(String(latestVerificationSummary.skippedCount))}</div>
      <div class="runtime-result-meta">first_failure=${escapeHtml(latestVerificationSummary.firstFailureSummary ? `${latestVerificationSummary.firstFailureSummary.label}: ${latestVerificationSummary.firstFailureSummary.detail}` : '-')}</div>
      <div class="actions">
        <button class="ghost-btn selected-preset-rerun-verification-btn" data-history-id="${escapeHtml(latestVerification.item.id)}">Rerun Verification</button>
      </div>
      <div class="runtime-result-list">
        ${representativeStepItemsHtml || '<div class="runtime-result-text">No representative verification steps recorded.</div>'}
      </div>
    </div>
  `;
}

export function renderSelectedPresetWorkflowCard({
  presetName,
  latestItem,
  latestWorkflowName,
  runtimeProfileDescription,
  runtimeMatch,
  totalRuns,
  issuesText,
  batchSelectionMeta,
  latestItemDetailHtml,
  verificationSectionHtml,
  actionsHtml,
  stepItemsHtml,
  lastFailureHtml,
  escapeHtml,
}) {
  return `
    <div class="runtime-result-card">
      <div class="runtime-result-head">
        <span class="runtime-result-title">${escapeHtml(presetName)}</span>
        <span class="runtime-pill ${latestItem.status === 'ok' ? 'optional' : latestItem.status === 'error' ? 'required' : 'neutral'}">${escapeHtml(latestItem.status || '-')}</span>
      </div>
      <div class="runtime-result-meta">runtime_profile=${escapeHtml(runtimeProfileDescription)}</div>
      <div class="runtime-result-meta">current_runtime=<span class="runtime-pill ${runtimeMatch.matchPillClass}">${escapeHtml(runtimeMatch.matchLabel)}</span></div>
      <div class="runtime-result-meta">latest_workflow=${escapeHtml(latestWorkflowName || '-')} | timestamp=${escapeHtml(latestItem.timestamp || '-')}</div>
      <div class="runtime-result-meta">total_runs=${escapeHtml(String(totalRuns))} | validation_issues=${escapeHtml(issuesText)}</div>
      <div class="runtime-result-meta">${batchSelectionMeta}</div>
      <div class="runtime-result-text">${escapeHtml(latestItem.summary || latestItem.title || '-')}</div>
      ${latestItemDetailHtml}
      ${verificationSectionHtml}
      <div class="actions">
        ${actionsHtml}
      </div>
      <div class="runtime-result-list">
        ${stepItemsHtml || '<div class="runtime-result-text">No workflow steps recorded.</div>'}
      </div>
      ${lastFailureHtml}
    </div>
  `;
}
