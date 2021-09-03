/*
Creates names.json used by mk-names-generator-2.py

At the bottom of this file, paste the definitions of "left" and "right" from:
  https://github.com/moby/moby/blob/master/pkg/namesgenerator/names-generator.go

Then:
  go run mk-names-generator-1.go
*/

package main

import (
	"encoding/json"
	"os"
)

type Words struct {
	Left  []string
	Right []string
}

func main() {
	f, _ := os.Create("names.json")
	defer f.Close()

	w := Words{left[:], right[:]}
	data, _ := json.Marshal(w)
	f.Write(data)
}

// paste definitions of "left" and "right" here...
