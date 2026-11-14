package static

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
	"time"
)

type parityReference struct {
	Queries       []string `json:"queries"`
	Dimension     int      `json:"dimension"`
	Labels        []string `json:"labels"`
	Cases         int      `json:"cases"`
	PublicCases   int      `json:"public_cases"`
	Tolerance     float64  `json:"tolerance"`
	VectorsFile   string   `json:"vectors_file"`
	ScoresFile    string   `json:"scores_file"`
	PythonLatency struct {
		P50 float64 `json:"p50_us"`
		P95 float64 `json:"p95_us"`
	} `json:"python_latency"`
}

func TestTokenizeBertWordPieceNormalizesAndSplits(t *testing.T) {
	vocab := map[string]uint32{
		"[UNK]":  0,
		"cafe":   1,
		",":      2,
		"run":    3,
		"##ning": 4,
		"!":      5,
	}

	got := tokenize("Café, RUNNING!", vocab, 0)
	want := []uint32{1, 2, 3, 4, 5}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("tokenize() = %v, want %v", got, want)
	}
}

func TestEncodeAndRankMatchPythonCentroidMath(t *testing.T) {
	model := Model{
		Dimension:  2,
		UnknownID:  2,
		Vocabulary: map[string]uint32{"x": 0, "y": 1, "[UNK]": 2},
		Embeddings: []float32{1, 0, 0, 1, 0, 0},
		Labels:     []string{"horizontal", "vertical"},
		Centroids:  []float32{1, 0, 0, 1},
	}

	vector, err := model.Embed("x y")
	if err != nil {
		t.Fatal(err)
	}
	if !closeEnough(vector[0], math.Sqrt(0.5), 1e-7) || !closeEnough(vector[1], math.Sqrt(0.5), 1e-7) {
		t.Fatalf("Embed() = %v, want unit mean", vector)
	}

	ranked, err := model.Rank("x")
	if err != nil {
		t.Fatal(err)
	}
	if len(ranked) != 2 || ranked[0].Label != "horizontal" || ranked[0].Score != 1 {
		t.Fatalf("Rank(x) = %v, want horizontal first with score 1", ranked)
	}
}

func TestEmbedOmitsUnknownTokensAndHandlesEmptyInput(t *testing.T) {
	model := Model{
		Dimension:  2,
		UnknownID:  1,
		Vocabulary: map[string]uint32{"x": 0, "[UNK]": 1},
		Embeddings: []float32{0, 2, 0, 0},
	}

	vector, err := model.Embed("unrecognized")
	if err != nil {
		t.Fatal(err)
	}
	if vector != nil {
		t.Fatalf("Embed(unrecognized) = %v, want nil vector", vector)
	}

	vector, err = model.Embed("x")
	if err != nil {
		t.Fatal(err)
	}
	if vector[0] != 0 || vector[1] != 1 {
		t.Fatalf("Embed(x) = %v, want [0 1]", vector)
	}
}

func TestEmbedTruncatesBeforeOmittingUnknownTokens(t *testing.T) {
	model := Model{
		Dimension:  2,
		MaxTokens:  2,
		UnknownID:  2,
		Vocabulary: map[string]uint32{"x": 0, "y": 1, "[UNK]": 2},
		Embeddings: []float32{1, 0, 0, 1, 0, 0},
	}

	vector, err := model.Embed("missing y x")
	if err != nil {
		t.Fatal(err)
	}
	if vector[0] != 0 || vector[1] != 1 {
		t.Fatalf("Embed(missing y x) = %v, want [0 1] after truncation", vector)
	}
}

func TestEmbedAppliesModel2VecCharacterLimitBeforeTokenization(t *testing.T) {
	model := Model{
		Dimension:     2,
		MaxCharacters: 1,
		UnknownID:     2,
		Vocabulary:    map[string]uint32{"x": 0, "y": 1, "[UNK]": 2},
		Embeddings:    []float32{1, 0, 0, 1, 0, 0},
	}

	vector, err := model.Embed("xy")
	if err != nil {
		t.Fatal(err)
	}
	if vector[0] != 1 || vector[1] != 0 {
		t.Fatalf("Embed(xy) = %v, want [1 0] after character truncation", vector)
	}
}

func TestEmbedRequiresUnknownIDToMatchVocabulary(t *testing.T) {
	model := Model{
		Dimension:  2,
		UnknownID:  1,
		Vocabulary: map[string]uint32{"x": 0},
		Embeddings: []float32{1, 0, 0, 1},
	}

	if _, err := model.Embed("x"); err == nil {
		t.Fatal("Embed() accepted a model without a matching [UNK] entry")
	}
}

func TestParityAgainstPythonReference(t *testing.T) {
	directory := os.Getenv("NEURON_PARITY_DIR")
	if directory == "" {
		t.Skip("set NEURON_PARITY_DIR to the exported Spike E reference")
	}
	model, err := Load(directory)
	if err != nil {
		t.Fatal(err)
	}
	metadataBytes, err := os.ReadFile(filepath.Join(directory, "parity.json"))
	if err != nil {
		t.Fatal(err)
	}
	var reference parityReference
	if err := json.Unmarshal(metadataBytes, &reference); err != nil {
		t.Fatal(err)
	}
	if len(reference.Queries) != reference.Cases || len(reference.Labels) != len(model.Labels) || reference.Dimension != model.Dimension {
		t.Fatal("parity metadata shape does not match exported model")
	}
	if !reflect.DeepEqual(reference.Labels, model.Labels) {
		t.Fatal("parity labels do not match exported model")
	}
	vectors, err := readFloat64(filepath.Join(directory, reference.VectorsFile))
	if err != nil {
		t.Fatal(err)
	}
	scores, err := readFloat64(filepath.Join(directory, reference.ScoresFile))
	if err != nil {
		t.Fatal(err)
	}
	if len(vectors) != reference.Cases*reference.Dimension || len(scores) != reference.Cases*len(reference.Labels) {
		t.Fatal("reference array shape does not match parity metadata")
	}

	maxVectorError, maxScoreError := 0.0, 0.0
	for row, query := range reference.Queries {
		vector, err := model.Embed(query)
		if err != nil {
			t.Fatalf("query %d: %v", row, err)
		}
		if len(vector) != reference.Dimension {
			t.Fatalf("query %d produced no embedding", row)
		}
		for column, value := range vector {
			maxVectorError = math.Max(maxVectorError, math.Abs(value-vectors[row*reference.Dimension+column]))
		}
		ranked, err := model.Rank(query)
		if err != nil {
			t.Fatalf("query %d: %v", row, err)
		}
		byLabel := make(map[string]float64, len(ranked))
		for _, result := range ranked {
			byLabel[result.Label] = result.Score
		}
		bestIndex := 0
		for column, label := range reference.Labels {
			expected := scores[row*len(reference.Labels)+column]
			maxScoreError = math.Max(maxScoreError, math.Abs(byLabel[label]-expected))
			if expected > scores[row*len(reference.Labels)+bestIndex] {
				bestIndex = column
			}
		}
		if ranked[0].Label != reference.Labels[bestIndex] {
			t.Fatalf("query %d winner = %q, Python winner = %q", row, ranked[0].Label, reference.Labels[bestIndex])
		}
	}
	t.Logf("cases=%d max_vector_abs_error=%.9g max_score_abs_error=%.9g tolerance=%.1e", reference.Cases, maxVectorError, maxScoreError, reference.Tolerance)
	if maxVectorError > reference.Tolerance || maxScoreError > reference.Tolerance {
		t.Fatalf("Go/Python parity exceeds tolerance: vector %.9g, score %.9g", maxVectorError, maxScoreError)
	}

	if reference.PublicCases < 1 || reference.PublicCases > len(reference.Queries) {
		t.Fatal("parity metadata has an invalid public query count")
	}
	publicQueries := reference.Queries[:reference.PublicCases]
	for _, query := range publicQueries {
		if _, err := model.Rank(query); err != nil {
			t.Fatal(err)
		}
	}
	latencySamples := make([]float64, 0, 20*len(publicQueries))
	for range 20 {
		for _, query := range publicQueries {
			started := time.Now()
			if _, err := model.Rank(query); err != nil {
				t.Fatal(err)
			}
			latencySamples = append(latencySamples, float64(time.Since(started).Nanoseconds())/1_000)
		}
	}
	sort.Float64s(latencySamples)
	p50 := latencySamples[(len(latencySamples)+1)/2-1]
	p95 := latencySamples[(95*len(latencySamples)+99)/100-1]
	t.Logf("latency calls=%d Go p50=%.1fus p95=%.1fus Python p50=%.1fus p95=%.1fus", len(latencySamples), p50, p95, reference.PythonLatency.P50, reference.PythonLatency.P95)
}

func readFloat64(path string) ([]float64, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if len(data)%8 != 0 {
		return nil, fmt.Errorf("%s has a byte length not divisible by eight", path)
	}
	values := make([]float64, len(data)/8)
	for index := range values {
		values[index] = math.Float64frombits(binary.LittleEndian.Uint64(data[index*8:]))
	}
	return values, nil
}

func closeEnough(got, want, tolerance float64) bool {
	return math.Abs(got-want) <= tolerance
}
