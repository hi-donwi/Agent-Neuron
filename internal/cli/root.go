// Package cli wires the neuron command tree. Commands are built by constructors
// rather than package-level globals so every test gets a fresh tree and its own
// output buffers.
package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

// NewRootCmd builds the full neuron command tree.
func NewRootCmd() *cobra.Command {
	root := &cobra.Command{
		Use:   "neuron",
		Short: "neuron - tiny specialist models for CPU-only machines",
		Long: `neuron runs tiny specialist models on machines with no GPU: a routing core,
knowledge packs, and small adapters over one shared base model.

The project is at milestone N0. Commands arrive with the milestones in ROADMAP.md.`,
		SilenceUsage:  true,
		SilenceErrors: true,
	}
	root.AddCommand(newVersionCmd())
	return root
}

// Execute runs neuron with the process arguments and exits non-zero on error.
func Execute() {
	code, msg := exitStatus(NewRootCmd().Execute())
	if msg != "" {
		fmt.Fprintln(os.Stderr, msg)
	}
	if code != 0 {
		os.Exit(code)
	}
}

// exitStatus maps a command error to the process exit code and the message to
// print.
func exitStatus(err error) (int, string) {
	if err == nil {
		return 0, ""
	}
	return 1, "neuron: " + err.Error()
}
