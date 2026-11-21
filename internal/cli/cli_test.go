package cli

import (
	"bytes"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"github.com/hi-donwi/Donwi-Neuron/internal/buildinfo"
)

func execute(t *testing.T, args ...string) (string, error) {
	t.Helper()
	var out bytes.Buffer
	cmd := NewRootCmd()
	cmd.SetOut(&out)
	cmd.SetErr(&out)
	cmd.SetArgs(args)
	err := cmd.Execute()
	return out.String(), err
}

func TestVersionPrintsOneHumanReadableLine(t *testing.T) {
	out, err := execute(t, "version")
	if err != nil {
		t.Fatalf("version: %v", err)
	}

	want := buildinfo.Get().String() + "\n"
	if out != want {
		t.Fatalf("version output = %q, want %q", out, want)
	}
}

func TestVersionJSONIsStable(t *testing.T) {
	out, err := execute(t, "version", "--json")
	if err != nil {
		t.Fatalf("version --json: %v", err)
	}

	var got map[string]string
	if err := json.Unmarshal([]byte(out), &got); err != nil {
		t.Fatalf("version --json is not JSON: %v\n%s", err, out)
	}
	for _, key := range []string{"version", "commit", "date", "go"} {
		if got[key] == "" {
			t.Errorf("version --json is missing %q: %s", key, out)
		}
	}
	if len(got) != 4 {
		t.Errorf("version --json has unexpected keys: %s", out)
	}
}

func TestVersionRejectsArguments(t *testing.T) {
	if _, err := execute(t, "version", "extra"); err == nil {
		t.Fatal("version with a positional argument must fail")
	}
}

func TestRootHelpNamesTheBinary(t *testing.T) {
	out, err := execute(t, "--help")
	if err != nil {
		t.Fatalf("--help: %v", err)
	}
	if !strings.Contains(out, "neuron") {
		t.Fatalf("help output does not name the binary:\n%s", out)
	}
}

func TestUnknownCommandFails(t *testing.T) {
	if _, err := execute(t, "no-such-command"); err == nil {
		t.Fatal("an unknown command must fail")
	}
}

func TestExitStatusMapsErrorsToANonZeroCodeAndAMessage(t *testing.T) {
	if code, msg := exitStatus(nil); code != 0 || msg != "" {
		t.Fatalf("exitStatus(nil) = %d, %q; want 0 and no message", code, msg)
	}

	code, msg := exitStatus(errors.New("boom"))
	if code != 1 {
		t.Errorf("exit code = %d, want 1", code)
	}
	if msg != "neuron: boom" {
		t.Errorf("message = %q, want %q", msg, "neuron: boom")
	}
}
