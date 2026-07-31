package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func newTestAppWithWorkspace(t *testing.T) *App {
	t.Helper()

	workspaceRoot := t.TempDir()
	cacheDir := filepath.Join(workspaceRoot, "data", "cache")
	if err := os.MkdirAll(cacheDir, 0o755); err != nil {
		t.Fatalf("failed to create cache directory: %v", err)
	}
	configsDir := filepath.Join(workspaceRoot, "configs")
	if err := os.MkdirAll(configsDir, 0o755); err != nil {
		t.Fatalf("failed to create configs directory: %v", err)
	}

	app := NewApp()
	app.workspaceRoot = workspaceRoot
	return app
}

func newTestAppAtWorkspace(workspaceRoot string) *App {
	app := NewApp()
	app.workspaceRoot = workspaceRoot
	return app
}

func TestSaveRequestReplacesOnlySameKind(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	if _, err := app.SaveRequest(SavedRequest{
		Name:   "shared-name",
		Kind:   "chat",
		Mode:   "fast",
		Prompt: "first prompt",
	}); err != nil {
		t.Fatalf("failed to save chat request: %v", err)
	}

	items, err := app.SaveRequest(SavedRequest{
		Name:   "shared-name",
		Kind:   "chat",
		Mode:   "work",
		Prompt: "updated prompt",
	})
	if err != nil {
		t.Fatalf("failed to replace chat request: %v", err)
	}

	if len(items) != 1 {
		t.Fatalf("expected 1 saved request after replace, got %d", len(items))
	}
	if items[0].Kind != "chat" || items[0].Mode != "work" || items[0].Prompt != "updated prompt" {
		t.Fatalf("saved request was not replaced as expected: %#v", items[0])
	}

	items, err = app.SaveRequest(SavedRequest{
		Name:   "shared-name",
		Kind:   "route",
		Mode:   "code",
		Prompt: "route prompt",
	})
	if err != nil {
		t.Fatalf("failed to save route request with same name: %v", err)
	}

	if len(items) != 2 {
		t.Fatalf("expected 2 saved requests across different kinds, got %d", len(items))
	}
}

func TestSaveRequestSupportsIndexRequestFields(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	items, err := app.SaveRequest(SavedRequest{
		Name:        "index-lab-notes",
		Kind:        "index",
		Project:     "lab",
		SourceQuery: "notes.md",
		Limit:       25,
	})
	if err != nil {
		t.Fatalf("failed to save index request: %v", err)
	}

	if len(items) != 1 {
		t.Fatalf("expected 1 saved request, got %d", len(items))
	}

	item := items[0]
	if item.Kind != "index" || item.Project != "lab" || item.SourceQuery != "notes.md" || item.Limit != 25 {
		t.Fatalf("saved index request fields did not persist as expected: %#v", item)
	}
}

func TestDeleteSavedRequestRespectsKind(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	seed := []SavedRequest{
		{Name: "shared-name", Kind: "chat", Prompt: "chat prompt"},
		{Name: "shared-name", Kind: "route", Prompt: "route prompt"},
		{Name: "other-name", Kind: "chat", Prompt: "other prompt"},
	}
	if err := app.writeSavedRequests(seed); err != nil {
		t.Fatalf("failed to seed saved requests: %v", err)
	}

	items, err := app.DeleteSavedRequest(LocalConfigNameRequest{
		Name: "shared-name",
		Kind: "route",
	})
	if err != nil {
		t.Fatalf("failed to delete saved request: %v", err)
	}

	if len(items) != 2 {
		t.Fatalf("expected 2 saved requests after kind-aware delete, got %d", len(items))
	}

	for _, item := range items {
		if item.Name == "shared-name" && item.Kind == "route" {
			t.Fatalf("route request with shared name should have been deleted: %#v", item)
		}
	}

	var foundChatShared bool
	for _, item := range items {
		if item.Name == "shared-name" && item.Kind == "chat" {
			foundChatShared = true
		}
	}
	if !foundChatShared {
		t.Fatal("chat request with same name should have been preserved")
	}
}

func TestRecordExecutionPrependsAndPersistsTrimmedItem(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	if err := app.writeExecutionHistory([]ExecutionHistoryItem{{
		ID:        "older-item",
		Timestamp: "2026-07-01T00:00:00Z",
		Kind:      "chat",
		Title:     "Older Item",
		Status:    "ok",
		Summary:   "older",
	}}); err != nil {
		t.Fatalf("failed to seed execution history: %v", err)
	}

	items, err := app.RecordExecution(ExecutionHistoryItem{
		Kind:    " workflow ",
		Title:   " Runtime Smoke ",
		Status:  " ok ",
		Summary: " summary with spaces ",
		Detail:  "detail",
		Payload: `{"workflow":"runtime_smoke"}`,
	})
	if err != nil {
		t.Fatalf("failed to record execution: %v", err)
	}

	if len(items) != 2 {
		t.Fatalf("expected 2 execution history items, got %d", len(items))
	}

	latest := items[0]
	if latest.Kind != "workflow" || latest.Title != "Runtime Smoke" || latest.Status != "ok" || latest.Summary != "summary with spaces" {
		t.Fatalf("recorded item was not trimmed as expected: %#v", latest)
	}
	if latest.ID == "" {
		t.Fatal("recorded item should have an auto-generated id")
	}
	if latest.Timestamp == "" {
		t.Fatal("recorded item should have an auto-generated timestamp")
	}
	if items[1].ID != "older-item" {
		t.Fatalf("expected older item to remain after prepending, got %#v", items[1])
	}

	persisted, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(persisted) != 2 || persisted[0].ID != latest.ID {
		t.Fatalf("persisted execution history did not match latest record: %#v", persisted)
	}
}

func TestRecordExecutionKeepsNewestFortyItems(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	for i := 0; i < 41; i++ {
		_, err := app.RecordExecution(ExecutionHistoryItem{
			ID:        fmt.Sprintf("item-%02d", i),
			Timestamp: "2026-07-01T00:00:00Z",
			Kind:      "workflow",
			Title:     "Workflow Item",
			Status:    "ok",
			Summary:   "bounded history",
		})
		if err != nil {
			t.Fatalf("failed to record execution item %d: %v", i, err)
		}
	}

	items, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(items) != 40 {
		t.Fatalf("expected execution history to keep 40 items, got %d", len(items))
	}
	if items[0].ID != "item-40" {
		t.Fatalf("expected newest item first, got %q", items[0].ID)
	}
	for _, item := range items {
		if item.ID == "item-00" {
			t.Fatalf("expected oldest item to be dropped, but found %#v", item)
		}
	}
}

func TestRunRuntimeStackActionRecordsUnsupportedAction(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	response, err := app.RunRuntimeStackAction(RuntimeStackActionRequest{Action: "restart_everything"})
	if err != nil {
		t.Fatalf("RunRuntimeStackAction returned unexpected error: %v", err)
	}
	if response == nil {
		t.Fatal("expected workflow response")
	}
	if response.Workflow != "runtime_restart_everything" {
		t.Fatalf("unexpected workflow name: %q", response.Workflow)
	}
	if response.Status != "error" {
		t.Fatalf("expected error status for unsupported action, got %q", response.Status)
	}
	if len(response.Steps) != 1 || response.Steps[0].Status != "failed" {
		t.Fatalf("expected a single failed workflow step, got %#v", response.Steps)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}

	recorded := history[0]
	if recorded.Kind != "workflow" || recorded.Status != "error" || recorded.Title != "Workflow (runtime_restart_everything)" {
		t.Fatalf("unexpected recorded history item: %#v", recorded)
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(recorded.Payload), &payload); err != nil {
		t.Fatalf("failed to unmarshal workflow payload: %v", err)
	}
	if payload["workflow"] != "runtime_restart_everything" {
		t.Fatalf("unexpected payload workflow: %#v", payload)
	}
	if payload["action"] != "restart_everything" {
		t.Fatalf("unexpected payload action: %#v", payload)
	}
}

func TestRunRuntimeConfigActionSaveAndDeleteLocalConfig(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	saveResponse, err := app.RunRuntimeConfigAction(RuntimeConfigActionRequest{
		Action:  "save_local_config",
		Name:    "rag.local.yaml",
		Content: "rag:\n  embedding_provider: local_hash\n",
	})
	if err != nil {
		t.Fatalf("RunRuntimeConfigAction(save) returned unexpected error: %v", err)
	}
	if saveResponse == nil || saveResponse.Workflow != "runtime_save_local_config" || saveResponse.Status != "ok" {
		t.Fatalf("unexpected save workflow response: %#v", saveResponse)
	}

	savedPath := filepath.Join(app.workspaceRoot, "configs", "rag.local.yaml")
	savedData, err := os.ReadFile(savedPath)
	if err != nil {
		t.Fatalf("failed to read saved local config: %v", err)
	}
	if string(savedData) != "rag:\n  embedding_provider: local_hash\n" {
		t.Fatalf("unexpected saved local config content: %q", string(savedData))
	}

	deleteResponse, err := app.RunRuntimeConfigAction(RuntimeConfigActionRequest{
		Action: "delete_local_config",
		Name:   "rag.local.yaml",
	})
	if err != nil {
		t.Fatalf("RunRuntimeConfigAction(delete) returned unexpected error: %v", err)
	}
	if deleteResponse == nil || deleteResponse.Workflow != "runtime_delete_local_config" || deleteResponse.Status != "ok" {
		t.Fatalf("unexpected delete workflow response: %#v", deleteResponse)
	}
	if _, err := os.Stat(savedPath); !os.IsNotExist(err) {
		t.Fatalf("expected local config to be deleted, stat err=%v", err)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 2 {
		t.Fatalf("expected 2 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (runtime_delete_local_config)" || history[1].Title != "Workflow (runtime_save_local_config)" {
		t.Fatalf("unexpected execution history order: %#v", history)
	}
}

func TestRunRuntimeConfigActionRecordsUnsupportedAction(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	response, err := app.RunRuntimeConfigAction(RuntimeConfigActionRequest{
		Action: "rewrite_everything",
		Name:   "rag.local.yaml",
	})
	if err != nil {
		t.Fatalf("RunRuntimeConfigAction returned unexpected error: %v", err)
	}
	if response == nil || response.Workflow != "runtime_rewrite_everything" || response.Status != "error" {
		t.Fatalf("unexpected runtime config workflow response: %#v", response)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &payload); err != nil {
		t.Fatalf("failed to unmarshal runtime config payload: %v", err)
	}
	if payload["workflow"] != "runtime_rewrite_everything" || payload["action"] != "rewrite_everything" {
		t.Fatalf("unexpected runtime config payload: %#v", payload)
	}
}

func TestRunRuntimeServiceActionRecordsUnsupportedAction(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	response, err := app.RunRuntimeServiceAction(RuntimeServiceActionRequest{
		Action: "toggle_everything",
		Watch: WatchRequest{
			Paths:    []string{"data/docs"},
			Project:  "lab",
			Interval: 2,
		},
	})
	if err != nil {
		t.Fatalf("RunRuntimeServiceAction returned unexpected error: %v", err)
	}
	if response == nil || response.Workflow != "runtime_toggle_everything" || response.Status != "error" {
		t.Fatalf("unexpected runtime service workflow response: %#v", response)
	}
	if len(response.Steps) != 1 || response.Steps[0].Status != "failed" {
		t.Fatalf("expected failed runtime service step, got %#v", response.Steps)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &payload); err != nil {
		t.Fatalf("failed to unmarshal runtime service payload: %v", err)
	}
	if payload["workflow"] != "runtime_toggle_everything" || payload["action"] != "toggle_everything" {
		t.Fatalf("unexpected runtime service payload: %#v", payload)
	}
	if _, ok := payload["watch"].(map[string]any); !ok {
		t.Fatalf("expected watch payload to be recorded, got %#v", payload["watch"])
	}
}

func TestRunPresetVerificationRecordsMissingRepresentativeRequests(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	preset := ProjectPreset{Name: "empty-preset"}

	response, err := app.RunPresetVerification(preset)
	if err != nil {
		t.Fatalf("RunPresetVerification returned unexpected error: %v", err)
	}
	if response == nil || response.Workflow != "preset_verification" || response.Status != "error" {
		t.Fatalf("unexpected preset verification response: %#v", response)
	}
	if len(response.Steps) != 1 || response.Steps[0].Status != "failed" {
		t.Fatalf("expected a single failed step, got %#v", response.Steps)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_verification)" || history[0].Status != "error" {
		t.Fatalf("unexpected history item: %#v", history[0])
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &payload); err != nil {
		t.Fatalf("failed to unmarshal preset verification payload: %v", err)
	}
	if payload["workflow"] != "preset_verification" || payload["preset_name"] != "empty-preset" {
		t.Fatalf("unexpected preset verification payload: %#v", payload)
	}
}

func TestRunPresetValidateRecordsHistory(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	preset := ProjectPreset{Name: "empty-preset"}

	response, err := app.RunPresetValidate(preset)
	if err != nil {
		t.Fatalf("RunPresetValidate returned unexpected error: %v", err)
	}
	if response == nil || response.Workflow != "preset_validate" || response.Status != "error" {
		t.Fatalf("unexpected preset validate response: %#v", response)
	}
	if len(response.Steps) == 0 {
		t.Fatalf("expected validation steps, got %#v", response)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_validate)" || history[0].Status != "error" {
		t.Fatalf("unexpected history item: %#v", history[0])
	}
}

func TestRunPresetSmokeRecordsHistory(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	preset := ProjectPreset{Name: "empty-preset"}

	response, err := app.RunPresetSmoke(preset)
	if err != nil {
		t.Fatalf("RunPresetSmoke returned unexpected error: %v", err)
	}
	if response == nil || response.Workflow != "preset_smoke" || response.Status != "error" {
		t.Fatalf("unexpected preset smoke response: %#v", response)
	}
	if len(response.Steps) == 0 {
		t.Fatalf("expected smoke steps, got %#v", response)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_smoke)" || history[0].Status != "error" {
		t.Fatalf("unexpected history item: %#v", history[0])
	}
}

func TestRunBatchPresetValidateRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetValidate(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Validate" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_validate)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch validate summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch validate summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_validate" {
		t.Fatalf("unexpected batch validate workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunBatchPresetSmokeRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetSmoke(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Smoke" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_smoke)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch smoke summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch smoke summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_smoke" {
		t.Fatalf("unexpected batch smoke workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunBatchPresetVerificationRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetVerification(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Verification" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for missing representative requests, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_verification)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_verification" {
		t.Fatalf("unexpected batch summary workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunBatchPresetWatchRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetWatch(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Watch" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_watch)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch watch summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch watch summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_watch" {
		t.Fatalf("unexpected batch watch workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunPresetRuntimeStackPrepareRecordsHistory(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	preset := ProjectPreset{Name: "runtime-preset"}

	response, err := app.RunPresetRuntimeStackPrepare(preset)
	if err != nil {
		t.Fatalf("RunPresetRuntimeStackPrepare returned unexpected error: %v", err)
	}
	if response == nil || response.Workflow != "preset_runtime_stack_prepare" || response.Status != "error" {
		t.Fatalf("unexpected preset runtime stack prepare response: %#v", response)
	}
	if len(response.Steps) == 0 {
		t.Fatalf("expected runtime stack prepare steps, got %#v", response)
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 execution history item, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_runtime_stack_prepare)" || history[0].Status != "error" {
		t.Fatalf("unexpected history item: %#v", history[0])
	}
}

func TestRunBatchPresetRuntimeStackPrepareRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetRuntimeStackPrepare(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Runtime + Stack Prepare" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_runtime_stack_prepare)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch runtime+stack summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch runtime+stack summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_runtime_stack_prepare" {
		t.Fatalf("unexpected batch runtime+stack workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunBatchPresetIngestEvalRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetIngestEval(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Ingest + Eval" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_ingest_eval)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch ingest+eval summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch ingest+eval summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_ingest_eval" {
		t.Fatalf("unexpected batch ingest+eval workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunBatchPresetEvalRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetEval(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Eval" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_eval)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch eval summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch eval summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_eval" {
		t.Fatalf("unexpected batch eval workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestRunBatchPresetIngestRecordsBatchSummary(t *testing.T) {
	app := newTestAppWithWorkspace(t)
	presets := []ProjectPreset{
		{Name: "preset-a"},
		{Name: "preset-b"},
	}

	app.runBatchPresetIngest(presets)

	state := app.GetBatchWorkflowState()
	if state == nil {
		t.Fatal("expected batch workflow state")
	}
	if state.WorkflowLabel != "Batch Preset Ingest" || state.Status != "failed" || state.Running {
		t.Fatalf("unexpected batch workflow state: %#v", state)
	}
	if len(state.Results) != 2 {
		t.Fatalf("expected 2 batch results, got %d", len(state.Results))
	}
	for _, result := range state.Results {
		if result.Status != "error" {
			t.Fatalf("expected error result for invalid presets, got %#v", result)
		}
	}

	history, err := app.readExecutionHistory()
	if err != nil {
		t.Fatalf("failed to read execution history: %v", err)
	}
	if len(history) != 3 {
		t.Fatalf("expected 3 execution history items, got %d", len(history))
	}
	if history[0].Title != "Workflow (preset_batch_ingest)" || history[0].Status != "error" {
		t.Fatalf("unexpected batch ingest summary history item: %#v", history[0])
	}

	var summaryPayload map[string]any
	if err := json.Unmarshal([]byte(history[0].Payload), &summaryPayload); err != nil {
		t.Fatalf("failed to unmarshal batch ingest summary payload: %v", err)
	}
	if summaryPayload["workflow"] != "preset_batch_ingest" {
		t.Fatalf("unexpected batch ingest workflow: %#v", summaryPayload)
	}
	if batchNames, ok := summaryPayload["batch_preset_names"].([]any); !ok || len(batchNames) != 2 {
		t.Fatalf("unexpected batch preset names payload: %#v", summaryPayload["batch_preset_names"])
	}
	if batchResults, ok := summaryPayload["batch_results"].([]any); !ok || len(batchResults) != 2 {
		t.Fatalf("unexpected batch results payload: %#v", summaryPayload["batch_results"])
	}
}

func TestBatchWorkflowStatePersistsAcrossAppInstances(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	state := app.SetBatchWorkflowState(BatchWorkflowState{
		WorkflowLabel:   "Batch Preset Verification",
		Status:          "running",
		Running:         true,
		CancelRequested: false,
		Results: []BatchWorkflowResultItem{
			{PresetName: "preset-a", Status: "running", Detail: "Running verification..."},
			{PresetName: "preset-b", Status: "queued", Detail: "Waiting to start."},
		},
	})
	if state == nil || state.WorkflowLabel != "Batch Preset Verification" {
		t.Fatalf("unexpected stored batch state: %#v", state)
	}

	restoredApp := newTestAppAtWorkspace(app.workspaceRoot)
	restoredState := restoredApp.GetBatchWorkflowState()
	if restoredState == nil {
		t.Fatal("expected batch workflow state to be restored from disk")
	}
	if restoredState.WorkflowLabel != "Batch Preset Verification" || restoredState.Status != "running" || !restoredState.Running {
		t.Fatalf("unexpected restored batch state: %#v", restoredState)
	}
	if len(restoredState.Results) != 2 || restoredState.Results[0].PresetName != "preset-a" {
		t.Fatalf("unexpected restored batch results: %#v", restoredState.Results)
	}

	cleared := restoredApp.ClearBatchWorkflowState()
	if cleared != nil {
		t.Fatalf("expected cleared batch state to be nil, got %#v", cleared)
	}

	emptyApp := newTestAppAtWorkspace(app.workspaceRoot)
	if emptyApp.GetBatchWorkflowState() != nil {
		t.Fatalf("expected cleared batch workflow state to stay removed")
	}
}

func TestRegressionWatchSettingsPersistAcrossAppInstances(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	settings := app.SetRegressionWatchSettings(RegressionWatchSettings{
		SourceHitDrop:  -0.25,
		IncludePreset:  true,
		IncludeDataset: false,
	})
	if settings.SourceHitDrop != 0 {
		t.Fatalf("expected negative source hit drop to normalize to 0, got %#v", settings)
	}
	if !settings.IncludePreset || settings.IncludeDataset {
		t.Fatalf("unexpected normalized settings: %#v", settings)
	}

	restoredApp := newTestAppAtWorkspace(app.workspaceRoot)
	restored := restoredApp.GetRegressionWatchSettings()
	if restored.SourceHitDrop != 0 || !restored.IncludePreset || restored.IncludeDataset {
		t.Fatalf("unexpected restored regression watch settings: %#v", restored)
	}

	updated := restoredApp.SetRegressionWatchSettings(RegressionWatchSettings{
		SourceHitDrop:  0.05,
		IncludePreset:  false,
		IncludeDataset: true,
	})
	if updated.SourceHitDrop != 0.05 || updated.IncludePreset || !updated.IncludeDataset {
		t.Fatalf("unexpected updated regression watch settings: %#v", updated)
	}

	reloadedApp := newTestAppAtWorkspace(app.workspaceRoot)
	reloaded := reloadedApp.GetRegressionWatchSettings()
	if reloaded.SourceHitDrop != 0.05 || reloaded.IncludePreset || !reloaded.IncludeDataset {
		t.Fatalf("unexpected reloaded regression watch settings: %#v", reloaded)
	}
}

func TestRegressionWatchProfilesPersistCustomProfilesAcrossAppInstances(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	profiles := app.SetRegressionWatchProfiles(map[string]RegressionWatchProfile{
		" strict_custom ": {
			Label:          "  Strict Custom  ",
			SourceHitDrop:  0.12,
			IncludePreset:  true,
			IncludeDataset: false,
			Builtin:        true,
		},
		"": {
			Label: "ignored",
		},
	})

	profile, ok := profiles["strict_custom"]
	if !ok {
		t.Fatalf("expected normalized custom profile key, got %#v", profiles)
	}
	if profile.Label != "Strict Custom" || profile.SourceHitDrop != 0.12 || !profile.IncludePreset || profile.IncludeDataset || profile.Builtin {
		t.Fatalf("unexpected normalized profile: %#v", profile)
	}
	if len(profiles) != 1 {
		t.Fatalf("expected only one normalized custom profile, got %#v", profiles)
	}

	restoredApp := newTestAppAtWorkspace(app.workspaceRoot)
	restored := restoredApp.GetRegressionWatchProfiles()
	restoredProfile, ok := restored["strict_custom"]
	if !ok {
		t.Fatalf("expected restored custom profile, got %#v", restored)
	}
	if restoredProfile.Label != "Strict Custom" || restoredProfile.SourceHitDrop != 0.12 || restoredProfile.Builtin {
		t.Fatalf("unexpected restored custom profile: %#v", restoredProfile)
	}

	cleared := restoredApp.SetRegressionWatchProfiles(map[string]RegressionWatchProfile{})
	if len(cleared) != 0 {
		t.Fatalf("expected cleared custom profiles, got %#v", cleared)
	}

	reloadedApp := newTestAppAtWorkspace(app.workspaceRoot)
	if profiles := reloadedApp.GetRegressionWatchProfiles(); len(profiles) != 0 {
		t.Fatalf("expected cleared custom profiles to stay removed, got %#v", profiles)
	}
}

func TestBatchPresetSelectionPersistsAcrossAppInstances(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	selection := app.SetBatchPresetSelection([]string{" preset-a ", "", "preset-b", "preset-a"})
	if len(selection) != 2 || selection[0] != "preset-a" || selection[1] != "preset-b" {
		t.Fatalf("unexpected normalized batch preset selection: %#v", selection)
	}

	restoredApp := newTestAppAtWorkspace(app.workspaceRoot)
	restoredSelection := restoredApp.GetBatchPresetSelection()
	if len(restoredSelection) != 2 || restoredSelection[0] != "preset-a" || restoredSelection[1] != "preset-b" {
		t.Fatalf("unexpected restored batch preset selection: %#v", restoredSelection)
	}

	cleared := restoredApp.ClearBatchPresetSelection()
	if len(cleared) != 0 {
		t.Fatalf("expected cleared selection to be empty, got %#v", cleared)
	}

	emptyApp := newTestAppAtWorkspace(app.workspaceRoot)
	if restored := emptyApp.GetBatchPresetSelection(); len(restored) != 0 {
		t.Fatalf("expected cleared batch preset selection to stay removed, got %#v", restored)
	}
}

func TestBatchPresetSelectionFallsBackToPersistedWorkflowState(t *testing.T) {
	app := newTestAppWithWorkspace(t)

	app.SetBatchWorkflowState(BatchWorkflowState{
		WorkflowLabel: "Batch Preset Verification",
		Status:        "running",
		Running:       true,
		Results: []BatchWorkflowResultItem{
			{PresetName: "preset-a", Status: "running", Detail: "Running verification..."},
			{PresetName: "preset-b", Status: "queued", Detail: "Waiting to start."},
		},
	})

	if err := app.clearBatchPresetSelectionFile(); err != nil {
		t.Fatalf("failed to clear explicit batch preset selection file: %v", err)
	}

	restoredApp := newTestAppAtWorkspace(app.workspaceRoot)
	restoredSelection := restoredApp.GetBatchPresetSelection()
	if len(restoredSelection) != 2 || restoredSelection[0] != "preset-a" || restoredSelection[1] != "preset-b" {
		t.Fatalf("expected selection to fall back to persisted workflow state, got %#v", restoredSelection)
	}

	secondRestore := newTestAppAtWorkspace(app.workspaceRoot)
	secondSelection := secondRestore.GetBatchPresetSelection()
	if len(secondSelection) != 2 || secondSelection[0] != "preset-a" || secondSelection[1] != "preset-b" {
		t.Fatalf("expected recovered selection to be re-persisted, got %#v", secondSelection)
	}
}
