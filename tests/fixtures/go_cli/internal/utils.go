package internal

import "strings"

// FormatName trims and title-cases a name.
func FormatName(name string) string {
	return strings.TrimSpace(strings.Title(name))
}
