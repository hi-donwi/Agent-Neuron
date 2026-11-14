// Package static runs model2vec-compatible static embeddings and centroid scoring.
package static

import (
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode"

	"golang.org/x/text/unicode/norm"
)

const maxWordCharacters = 100

// Model is a static token table and optional set of unit centroids.
type Model struct {
	Dimension     int
	MaxTokens     int
	MaxCharacters int
	UnknownID     int
	Vocabulary    map[string]uint32
	Embeddings    []float32
	Labels        []string
	Centroids     []float32
}

// Result is a label and its cosine similarity to the embedded query.
type Result struct {
	Label string  `json:"label"`
	Score float64 `json:"score"`
}

type manifest struct {
	Dimension     int               `json:"dimension"`
	MaxTokens     int               `json:"max_tokens"`
	MaxCharacters int               `json:"max_characters"`
	UnknownID     int               `json:"unknown_id"`
	Vocabulary    map[string]uint32 `json:"vocabulary"`
	Labels        []string          `json:"labels"`
}

// Load reads the portable format emitted by lab/spikes/export_static.py.
func Load(directory string) (*Model, error) {
	manifestBytes, err := os.ReadFile(filepath.Join(directory, "model.json"))
	if err != nil {
		return nil, fmt.Errorf("read model manifest: %w", err)
	}
	var metadata manifest
	if err := json.Unmarshal(manifestBytes, &metadata); err != nil {
		return nil, fmt.Errorf("parse model manifest: %w", err)
	}
	if metadata.Dimension < 1 || len(metadata.Vocabulary) == 0 {
		return nil, errors.New("model manifest must include a positive dimension and vocabulary")
	}

	embeddings, err := readFloat32(filepath.Join(directory, "embeddings.f32"))
	if err != nil {
		return nil, fmt.Errorf("read embedding table: %w", err)
	}
	model := &Model{
		Dimension:     metadata.Dimension,
		MaxTokens:     metadata.MaxTokens,
		MaxCharacters: metadata.MaxCharacters,
		UnknownID:     metadata.UnknownID,
		Vocabulary:    metadata.Vocabulary,
		Embeddings:    embeddings,
		Labels:        metadata.Labels,
	}
	if err := model.validate(); err != nil {
		return nil, err
	}
	if len(metadata.Labels) > 0 {
		model.Centroids, err = readFloat32(filepath.Join(directory, "centroids.f32"))
		if err != nil {
			return nil, fmt.Errorf("read centroid table: %w", err)
		}
		if len(model.Centroids) != len(model.Labels)*model.Dimension {
			return nil, errors.New("centroid table shape does not match labels and dimension")
		}
	}
	return model, nil
}

func readFloat32(path string) ([]float32, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if len(data)%4 != 0 {
		return nil, fmt.Errorf("%s has a byte length not divisible by four", path)
	}
	values := make([]float32, len(data)/4)
	for i := range values {
		values[i] = math.Float32frombits(binary.LittleEndian.Uint32(data[i*4:]))
	}
	return values, nil
}

func (model Model) validate() error {
	if model.Dimension < 1 || len(model.Embeddings) == 0 || len(model.Embeddings)%model.Dimension != 0 {
		return errors.New("embedding table shape does not match dimension")
	}
	rows := len(model.Embeddings) / model.Dimension
	if err := model.validateUnknownID(rows); err != nil {
		return err
	}
	if model.MaxTokens < 0 || model.MaxCharacters < 0 {
		return errors.New("token and character limits cannot be negative")
	}
	for token, id := range model.Vocabulary {
		if int(id) >= rows {
			return fmt.Errorf("token %q has id %d outside embedding table", token, id)
		}
	}
	return nil
}

func (model Model) validateUnknownID(rows int) error {
	if model.UnknownID < 0 || model.UnknownID >= rows {
		return errors.New("unknown token id is outside embedding table")
	}
	if id, ok := model.Vocabulary["[UNK]"]; !ok || int(id) != model.UnknownID {
		return errors.New("unknown token id does not match the [UNK] vocabulary entry")
	}
	return nil
}

// Embed applies BERT normalization and WordPiece tokenization, means the token vectors,
// and L2-normalizes the result. Unknown WordPiece IDs are omitted like model2vec.
func (model Model) Embed(text string) ([]float64, error) {
	if model.Dimension < 1 || len(model.Embeddings) == 0 || len(model.Embeddings)%model.Dimension != 0 {
		return nil, errors.New("embedding table shape does not match dimension")
	}
	if err := model.validateUnknownID(len(model.Embeddings) / model.Dimension); err != nil {
		return nil, err
	}
	if model.MaxTokens < 0 || model.MaxCharacters < 0 {
		return nil, errors.New("token and character limits cannot be negative")
	}
	if model.MaxCharacters > 0 && len(text) > model.MaxCharacters {
		text = truncateRunes(text, model.MaxCharacters)
	}
	ids := tokenize(text, model.Vocabulary, model.UnknownID)
	if model.MaxTokens > 0 && len(ids) > model.MaxTokens {
		ids = ids[:model.MaxTokens]
	}
	known := ids[:0]
	for _, id := range ids {
		if int(id) != model.UnknownID {
			known = append(known, id)
		}
	}
	ids = known
	if len(ids) == 0 {
		return nil, nil
	}
	vector := make([]float64, model.Dimension)
	for _, id := range ids {
		if int(id) >= len(model.Embeddings)/model.Dimension {
			return nil, fmt.Errorf("token id %d is outside embedding table", id)
		}
		start := int(id) * model.Dimension
		for i, value := range model.Embeddings[start : start+model.Dimension] {
			vector[i] += float64(value)
		}
	}
	for i := range vector {
		vector[i] /= float64(len(ids))
	}
	if !normalize(vector) {
		return vector, nil
	}
	return vector, nil
}

func truncateRunes(text string, max int) string {
	count := 0
	for index := range text {
		if count == max {
			return text[:index]
		}
		count++
	}
	return text
}

// Rank returns labels in descending cosine similarity, preserving manifest order on ties.
func (model Model) Rank(text string) ([]Result, error) {
	if len(model.Labels) == 0 || len(model.Centroids) != len(model.Labels)*model.Dimension {
		return nil, errors.New("model has no valid centroid table")
	}
	vector, err := model.Embed(text)
	if err != nil || vector == nil {
		return nil, err
	}
	results := make([]Result, len(model.Labels))
	for label, name := range model.Labels {
		start := label * model.Dimension
		score := 0.0
		for i, value := range vector {
			score += value * float64(model.Centroids[start+i])
		}
		results[label] = Result{Label: name, Score: score}
	}
	sort.SliceStable(results, func(i, j int) bool { return results[i].Score > results[j].Score })
	return results, nil
}

func normalize(vector []float64) bool {
	squared := 0.0
	for _, value := range vector {
		squared += value * value
	}
	if squared == 0 {
		return false
	}
	length := math.Sqrt(squared)
	for i := range vector {
		vector[i] /= length
	}
	return true
}

func tokenize(text string, vocabulary map[string]uint32, unknownID int) []uint32 {
	normalized := normalizeBertText(text)
	words := splitBertPunctuation(normalized)
	ids := make([]uint32, 0, len(words))
	for _, word := range words {
		pieces, ok := wordPieces(word, vocabulary)
		if ok {
			ids = append(ids, pieces...)
		} else {
			ids = append(ids, uint32(unknownID))
		}
	}
	return ids
}

func normalizeBertText(text string) string {
	var result strings.Builder
	for _, r := range norm.NFD.String(strings.ToLower(text)) {
		if unicode.Is(unicode.Mn, r) {
			continue
		}
		if isBertWhitespace(r) {
			result.WriteByte(' ')
			continue
		}
		if r == 0 || r == '\uFFFD' || unicode.IsControl(r) || unicode.Is(unicode.Cf, r) {
			continue
		}
		if isChineseCharacter(r) {
			result.WriteByte(' ')
			result.WriteRune(r)
			result.WriteByte(' ')
			continue
		}
		result.WriteRune(r)
	}
	return result.String()
}

func splitBertPunctuation(text string) []string {
	var words []string
	var current strings.Builder
	flush := func() {
		if current.Len() > 0 {
			words = append(words, current.String())
			current.Reset()
		}
	}
	for _, r := range text {
		if isBertWhitespace(r) {
			flush()
		} else if isBertPunctuation(r) {
			flush()
			words = append(words, string(r))
		} else {
			current.WriteRune(r)
		}
	}
	flush()
	return words
}

func wordPieces(word string, vocabulary map[string]uint32) ([]uint32, bool) {
	characters := []rune(word)
	if len(characters) > maxWordCharacters {
		return nil, false
	}
	ids := make([]uint32, 0, len(characters))
	for start := 0; start < len(characters); {
		found := false
		for end := len(characters); end > start; end-- {
			piece := string(characters[start:end])
			if start > 0 {
				piece = "##" + piece
			}
			if id, ok := vocabulary[piece]; ok {
				ids = append(ids, id)
				start = end
				found = true
				break
			}
		}
		if !found {
			return nil, false
		}
	}
	return ids, true
}

func isBertWhitespace(r rune) bool {
	return unicode.IsSpace(r)
}

func isBertPunctuation(r rune) bool {
	if r >= 33 && r <= 47 || r >= 58 && r <= 64 || r >= 91 && r <= 96 || r >= 123 && r <= 126 {
		return true
	}
	return unicode.IsPunct(r)
}

func isChineseCharacter(r rune) bool {
	return r >= 0x4E00 && r <= 0x9FFF ||
		r >= 0x3400 && r <= 0x4DBF ||
		r >= 0x20000 && r <= 0x2A6DF ||
		r >= 0x2A700 && r <= 0x2B73F ||
		r >= 0x2B740 && r <= 0x2B81F ||
		r >= 0x2B820 && r <= 0x2CEAF ||
		r >= 0xF900 && r <= 0xFAFF ||
		r >= 0x2F800 && r <= 0x2FA1F
}
