package main

import (
	"testing"
)

func TestSmallSearch(t *testing.T) {
	parallelSearch([]string{"Llama-2-13B-chat-GGML"}, 1, "_test.yaml")
}
