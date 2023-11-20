package main

import (
	"os"
	"testing"
)

// This isn't much of a unit test - rather, this is intended to allow `go test` to serve as a developer's testing tool to see if the main process would handle a given model appropriately.
func TestSmallSearch(t *testing.T) {
	testQuery := os.Getenv("TEST_QUERY")
	outputPath := os.Getenv("TEST_OUTPUT")

	if testQuery == "" {
		testQuery = "Llama-2-13B-chat-GGML"
	}
	if outputPath == "" {
		outputPath = "_test.yaml"
	}
	parallelSearch([]string{testQuery}, 1, outputPath)
}
