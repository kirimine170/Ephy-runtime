package main

import "testing"

func TestValidateWebSourceURLAllowsPublicHTTPURLs(t *testing.T) {
	parsed, err := validateWebSourceURL("https://example.com/research?q=rag")
	if err != nil {
		t.Fatalf("expected public URL to be allowed: %v", err)
	}
	if parsed.Hostname() != "example.com" {
		t.Fatalf("unexpected hostname: %s", parsed.Hostname())
	}
}

func TestValidateWebSourceURLRejectsUnsafeTargets(t *testing.T) {
	tests := []string{
		"file:///etc/passwd",
		"javascript:alert(1)",
		"http://localhost/admin",
		"http://127.0.0.1/admin",
		"http://169.254.169.254/latest/meta-data",
		"https://user:password@example.com/",
		"https://service.company.internal/",
	}
	for _, target := range tests {
		if _, err := validateWebSourceURL(target); err == nil {
			t.Errorf("expected URL to be rejected: %s", target)
		}
	}
}
