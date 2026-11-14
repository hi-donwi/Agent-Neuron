package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/hi-donwi/Agent-Neuron/internal/router/static"
)

type retrievalRequest struct {
	ModelDir string   `json:"model_dir"`
	Texts    []string `json:"texts"`
}

func main() {
	var input retrievalRequest
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		fail(err)
	}
	model, err := static.Load(input.ModelDir)
	if err != nil {
		fail(err)
	}
	vectors := make([][]float64, len(input.Texts))
	for index, text := range input.Texts {
		vectors[index], err = model.Embed(text)
		if err != nil {
			fail(fmt.Errorf("embed text %d: %w", index, err))
		}
	}
	if err := json.NewEncoder(os.Stdout).Encode(map[string]any{"vectors": vectors}); err != nil {
		fail(err)
	}
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
