export function renderSinglePresetBatchActionButtons({buttonPrefix, presetName, escapeHtml}) {
  const normalizedPrefix = String(buttonPrefix || '').trim();
  const normalizedPresetName = escapeHtml(String(presetName || '').trim());
  return `
    <button class="ghost-btn ${normalizedPrefix}-run-batch-validate-btn" data-preset-name="${normalizedPresetName}">Run Batch Validate For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-smoke-btn" data-preset-name="${normalizedPresetName}">Run Batch Smoke For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-verification-btn" data-preset-name="${normalizedPresetName}">Run Batch Verification For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-watch-btn" data-preset-name="${normalizedPresetName}">Run Batch Watch For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-runtime-stack-prepare-btn" data-preset-name="${normalizedPresetName}">Run Batch Runtime + Stack For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-ingest-btn" data-preset-name="${normalizedPresetName}">Run Batch Ingest For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-eval-btn" data-preset-name="${normalizedPresetName}">Run Batch Eval For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-ingest-eval-btn" data-preset-name="${normalizedPresetName}">Run Batch Ingest + Eval For This Preset</button>
    <button class="ghost-btn ${normalizedPrefix}-run-batch-stack-btn" data-preset-name="${normalizedPresetName}">Run Batch Stack For This Preset</button>
  `;
}

export function renderPresetPrimaryActionButtons({buttonPrefix, presetName, runtimeProfile, escapeHtml}) {
  const normalizedPrefix = String(buttonPrefix || '').trim();
  const escapedPresetName = escapeHtml(String(presetName || '').trim());
  return `
    ${
      runtimeProfile === 'current'
        ? `<button class="ghost-btn ${normalizedPrefix}-open-runtime-btn">Open Runtime Controls</button>`
        : `
          <button class="ghost-btn ${normalizedPrefix}-apply-runtime-btn" data-preset-name="${escapedPresetName}">Apply Runtime Profile</button>
          <button class="primary-btn ${normalizedPrefix}-apply-runtime-stack-btn" data-preset-name="${escapedPresetName}">Apply Runtime + Start Stack</button>
        `
    }
    <button class="ghost-btn ${normalizedPrefix}-validate-btn" data-preset-name="${escapedPresetName}">Validate</button>
    <button class="primary-btn ${normalizedPrefix}-run-workflow-btn" data-preset-name="${escapedPresetName}">Start Stack + Ingest + Eval</button>
  `;
}

export function renderPresetBatchSelectionButtons({buttonPrefix, presetName, isSelected, escapeHtml}) {
  const normalizedPrefix = String(buttonPrefix || '').trim();
  const escapedPresetName = escapeHtml(String(presetName || '').trim());
  return `
    <button class="ghost-btn ${normalizedPrefix}-toggle-batch-btn" data-preset-name="${escapedPresetName}">${isSelected ? 'Remove From Batch' : 'Add To Batch'}</button>
    <button class="ghost-btn ${normalizedPrefix}-batch-only-btn" data-preset-name="${escapedPresetName}">Use As Only Batch Preset</button>
  `;
}

export function renderPresetBatchSelectionMeta({isSelected, escapeHtml}) {
  return `batch_selection=<span class="runtime-pill ${isSelected ? 'optional' : 'neutral'}">${escapeHtml(isSelected ? 'selected' : 'not selected')}</span>`;
}
