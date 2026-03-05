package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "go-cli",
	Short: "A minimal Go CLI tool",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Hello from go-cli!")
	},
}

func Execute() error {
	return rootCmd.Execute()
}
