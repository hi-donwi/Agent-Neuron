package cli

import (
	"encoding/json"
	"fmt"

	"github.com/hi-donwi/Donwi-Neuron/internal/buildinfo"
	"github.com/spf13/cobra"
)

func newVersionCmd() *cobra.Command {
	var asJSON bool
	cmd := &cobra.Command{
		Use:   "version",
		Short: "Print neuron build information",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			info := buildinfo.Get()
			if asJSON {
				return json.NewEncoder(cmd.OutOrStdout()).Encode(info)
			}
			_, err := fmt.Fprintln(cmd.OutOrStdout(), info.String())
			return err
		},
	}
	cmd.Flags().BoolVar(&asJSON, "json", false, "print build information as JSON")
	return cmd
}
