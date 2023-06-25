package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"regexp"
	"strings"

	. "github.com/go-skynet/LocalAI/pkg/gallery"
	"gopkg.in/yaml.v3"
)

var baseGalleryURL string = "github:go-skynet/model-gallery"
var baseConfig string = baseGalleryURL + "/base.yaml"

var baseURLs map[string]string = map[string]string{
	// This maps the key to a file into the repository
	"koala":       "koala",
	"manticore":   "manticore",
	"vicuna":      "vicuna",
	"airoboros":   "airoboros",
	"hypermantis": "hypermantis",
	"guanaco":     "guanaco",
	"openllama":   "openllama_3b",
	"rwkv":        "rwkv-raven-1b",
	"wizard":      "wizard",
}

type Model struct {
	ModelID string `json:"modelId"`
	Author  string `json:"author"`
}

type CardData struct{}

type HFModel struct {
	Author   string `json:"author"`
	CardData struct {
		Inference bool   `json:"inference"`
		License   string `json:"license"`
	} `json:"cardData"`
	Tags     []string  `json:"tags"`
	Siblings []Sibling `json:"siblings"`
	Files    []File
}

type Sibling struct {
	RFileName string `json:"rfilename"`
}

func main() {
	// Step 1: Get a list of all models
	resp, err := http.Get("https://huggingface.co/api/models?search=TheBloke")
	if err != nil {
		log.Fatal(err)
	}
	defer resp.Body.Close()

	var modelList []Model
	err = json.NewDecoder(resp.Body).Decode(&modelList)
	if err != nil {
		log.Fatal(err)
	}

	gallery := []GalleryModel{}
	// Step 2: Process each model and retrieve its files (siblings)
	for _, model := range modelList {
		fmt.Println("Model ID:", model.ModelID)

		// Step 3: Retrieve model files (siblings)
		m, err := getModel(model.ModelID)
		if err != nil {
			log.Println("Failed to retrieve files for model", model.ModelID)
			continue
		}

		// Step 4: Save the model files
		mm, err := getModelFiles(model.ModelID, m)
		if err != nil {
			log.Println("Failed to save files for model", model.ModelID)
			continue
		}

		for _, m := range mm.Files {
			url := baseConfig

			for k, v := range baseURLs {
				// Check if the model name or ID contains the key
				// TODO: This is a bit hacky, we should probably use a regex(?)
				if strings.Contains(strings.ToLower(m.Filename), k) || strings.Contains(strings.ToLower(model.ModelID), k) {
					url = fmt.Sprintf("%s/%s.yaml", baseGalleryURL, v)
					break
				}
			}

			gallery = append(gallery, GalleryModel{
				Name:        m.Filename,
				Description: model.ModelID,
				URLs:        []string{fmt.Sprintf("https://huggingface.co/%s", model.ModelID)},
				License:     mm.CardData.License,
				Icon:        "",
				Overrides: map[string]interface{}{
					"params": map[string]interface{}{
						"model": m.Filename,
					},
				},
				AdditionalFiles: []File{m},
				URL:             url,
				Tags:            mm.Tags,
			})
			fmt.Println("Found", m)
		}

		// Step 5: Save the gallery
		galleryYAML, err := yaml.Marshal(gallery)
		if err != nil {
			log.Fatal(err)
		}
		ioutil.WriteFile("index.yaml", galleryYAML, 0644)
	}
}

func getModel(modelID string) (HFModel, error) {
	var files HFModel

	resp, err := http.Get(fmt.Sprintf("https://huggingface.co/api/models/%s", modelID))
	if err != nil {
		return files, err
	}
	defer resp.Body.Close()

	err = json.NewDecoder(resp.Body).Decode(&files)
	if err != nil {
		return files, err
	}

	return files, nil
}

func getSHA256(url string) (string, error) {

	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("Failed to fetch the web page: %v\n", err)
	}
	defer resp.Body.Close()

	htmlData, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("Failed to read the response body: %v\n", err)
	}

	shaRegex := regexp.MustCompile(`(?s)<strong>SHA256:</strong>\s+(.+?)</li>`)
	match := shaRegex.FindSubmatch(htmlData)
	if len(match) < 2 {
		return "", fmt.Errorf("SHA256 value not found in the HTML")
	}

	sha := string(match[1])
	return sha, nil
}

func getModelFiles(repository string, modelFiles HFModel) (HFModel, error) {
	f := []File{}
	for _, sibling := range modelFiles.Siblings {
		if !strings.HasSuffix(sibling.RFileName, ".bin") {
			fmt.Println("not a bin ", sibling.RFileName)

			continue
		}
		if strings.HasPrefix(sibling.RFileName, "pytorch") {
			fmt.Println("pythorch", sibling.RFileName)

			continue
		}
		fileURL := fmt.Sprintf("https://huggingface.co/%s/resolve/main/%s", repository, sibling.RFileName)
		shaURL := fmt.Sprintf("https://huggingface.co/%s/blob/main/%s", repository, sibling.RFileName)
		sha, err := getSHA256(shaURL)
		if err != nil {

			fmt.Println("Failed to get etag", sibling.RFileName, err)
			continue
		}

		f = append(f, File{
			Filename: sibling.RFileName,
			SHA256:   sha,
			URI:      fileURL,
		})
		fmt.Println("Saving file", sibling.RFileName, sha)

	}
	modelFiles.Files = f
	return modelFiles, nil
}
