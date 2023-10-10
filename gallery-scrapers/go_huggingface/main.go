package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"

	. "github.com/go-skynet/LocalAI/pkg/gallery"
	"gopkg.in/yaml.v3"
)

const indexFile = "huggingface.yaml"

var baseGalleryURL string = "github:go-skynet/model-gallery"
var baseConfig string = baseGalleryURL + "/base.yaml"

func StripErrorFromPointer[T any](value *T, errs ...error) *T {
	if len(errs) > 0 && errs[0] != nil {
		return nil
	}
	return value
}

type BaseDefinition struct {
	Name  string
	Path  string
	Match *regexp.Regexp
}

// Currently these are matched top to bottom, with a break statement.
// What that means is if a model is named something like "LLama-Koala-Manticore-Wizard", whichever of those currently appears first in this list will "win".
// TODO: do we need a more sophisticated model than this?
// TODO: is the current list order even correct!
var baseDefinitions []BaseDefinition = []BaseDefinition{
	{
		Name: "koala",
		Path: "koala",
	},
	{
		Name: "koala",
		Path: "koala",
	},
	{
		Name: "manticore",
		Path: "manticore",
	},
	{
		Name: "vicuna",
		Path: "vicuna",
	},
	{
		Name: "airoboros",
		Path: "airoboros",
	},
	{
		Name: "hypermantis",
		Path: "hypermantis",
	},
	{
		Name: "guanaco",
		Path: "guanaco",
	},
	{
		Name: "openllama",
		Path: "openllama_3b",
	},
	{
		Name:  "llama2-chat",
		Path:  "llama2-chat",
		Match: StripErrorFromPointer(regexp.Compile(`llama-*2-*([\d]+b)?-*chat`)),
	},
	{
		Name:  "rwkv-world",
		Path:  "rwkv-world",
		Match: StripErrorFromPointer(regexp.Compile(`rwkv.*world`)),
	},
	{
		Name: "rwkv",
		Path: "rwkv-20b",
	},
	{
		Name: "wizard",
		Path: "wizard",
	},
	{
		Name: "hippogriff",
		Path: "hippogriff",
	},
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
		return "", fmt.Errorf("failed to fetch the web page: %v\n", err)
	}
	defer resp.Body.Close()

	htmlData, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read the response body: %v\n", err)
	}

	shaRegex := regexp.MustCompile(`(?s)<strong>SHA256:</strong>\s+(.+?)</li>`)
	match := shaRegex.FindSubmatch(htmlData)
	if len(match) < 2 {
		return "", fmt.Errorf("SHA256 value not found in the HTML. HTTP Status: %d", resp.StatusCode)
	}

	sha := string(match[1])
	return sha, nil
}

func getModelFiles(repository string, modelFiles HFModel) (HFModel, error) {
	f := []File{}
	for _, sibling := range modelFiles.Siblings {
		if !strings.HasSuffix(sibling.RFileName, ".bin") {
			continue
		}
		basePath := filepath.Base(sibling.RFileName)
		if strings.HasPrefix(basePath, "pytorch") {
			continue
		}
		fileURL := fmt.Sprintf("https://huggingface.co/%s/resolve/main/%s", repository, sibling.RFileName)
		shaURL := fmt.Sprintf("https://huggingface.co/%s/blob/main/%s", repository, sibling.RFileName)
		sha, err := getSHA256(shaURL)
		if err != nil {
			fmt.Println("Failed to get SHA for", sibling.RFileName, err)
			continue
		}
		f = append(f, File{
			Filename: sibling.RFileName,
			SHA256:   sha,
			URI:      fileURL,
		})
		fmt.Println("Model file:", sibling.RFileName, sha)
	}
	modelFiles.Files = f
	return modelFiles, nil
}

func scrape(concurrency int, modelIDs []string) []GalleryModel {
	currentGallery := []GalleryModel{}
	muLock := sync.Mutex{}
	wg := new(sync.WaitGroup)

	uris := make(chan string)
	models := make(chan GalleryModel)

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go scraperWorker(wg, uris, models)
	}

	go func() {
		for _, u := range modelIDs {
			uris <- u
		}
		close(uris)
	}()

	doneChan := make(chan bool, 1)
	go func() {
		fmt.Println("getting models results")
		for u := range models {
			fmt.Println("appending", u.Name)

			muLock.Lock()
			currentGallery = append(currentGallery, u)
			muLock.Unlock()
		}
		doneChan <- true
	}()

	wg.Wait()
	close(models)

	fmt.Println("Waiting for models")
	<-doneChan

	return currentGallery
}

func scraperWorker(wg *sync.WaitGroup, c chan string, g chan GalleryModel) {

	defer wg.Done()
	for model := range c {
		// Step 3: Retrieve model files (siblings)
		m, err := getModel(model)
		if err != nil {
			log.Println("Failed to retrieve files for model", model)
			continue
		}

		// Step 4: Save the model files
		mm, err := getModelFiles(model, m)
		if err != nil {
			log.Println("Failed to save files for model", model)
			continue
		}

		for _, m := range mm.Files {
			url := baseConfig

			for _, v := range baseDefinitions {
				// Check if the model name or filename matches this baseDefinition
				if v.Match != nil {
					// If an explicit Match regex exists, prefer that.
					if v.Match.MatchString((strings.ToLower(m.Filename))) || v.Match.MatchString((strings.ToLower(model))) { // TODO Do we need anything fancier than a boolean match? Might be interesting to capture group the # of parameters and feed that into a template somehow...
						url = fmt.Sprintf("%s/%s.yaml", baseGalleryURL, v.Path)
						break
					}
				} else {
					// Otherwise, fallback on the existing string match
					if strings.Contains(strings.ToLower(m.Filename), v.Name) || strings.Contains(strings.ToLower(model), v.Name) {
						url = fmt.Sprintf("%s/%s.yaml", baseGalleryURL, v.Path)
						break
					}
				}
			}

			modelName := strings.ReplaceAll(strings.ToLower(fmt.Sprintf("%s/%s", model, m.Filename)), "/", "__")
			g <- GalleryModel{
				Name:    modelName,
				URLs:    []string{fmt.Sprintf("https://huggingface.co/%s", model)},
				License: mm.CardData.License,
				Icon:    "",
				Overrides: map[string]interface{}{
					"parameters": map[string]interface{}{
						"model": m.Filename,
					},
				},
				AdditionalFiles: []File{m},
				URL:             url,
				Tags:            mm.Tags,
			}
		}
	}
}

func scrapeHuggingFace(term string, concurrency int, indexFile string) {
	// Step 1: Get a list of all models
	resp, err := http.Get(fmt.Sprintf("https://huggingface.co/api/models?search=%s", term))
	if err != nil {
		log.Fatal(err)
	}
	defer resp.Body.Close()

	var modelList []Model
	err = json.NewDecoder(resp.Body).Decode(&modelList)
	if err != nil {
		log.Fatal(err)
	}

	currentGallery := []GalleryModel{}
	currentGalleryMap := map[string]GalleryModel{}

	dat, err := os.ReadFile(indexFile)
	if err == nil {
		err = yaml.Unmarshal(dat, &currentGallery)
		if err != nil {
			log.Fatal(err)
		}
	}

	for _, model := range currentGallery {
		currentGalleryMap[model.Name] = model
	}

	//gallery := []GalleryModel{}
	ids := []string{}
	// Step 2: Process each model and retrieve its files (siblings)
	for _, model := range modelList {
		ids = append(ids, model.ModelID)
	}

	fmt.Println("Processing", len(ids), "models")

	gallery := scrape(concurrency, ids)

	for _, model := range gallery {
		currentGalleryMap[model.Name] = model
	}

	gallery = []GalleryModel{}

	for _, g := range currentGalleryMap {
		gallery = append(gallery, g)
	}

	sort.Slice(gallery, func(i, j int) bool {
		return gallery[i].Name < gallery[j].Name
	})

	// Step 5: Save the gallery
	galleryYAML, err := yaml.Marshal(gallery)
	if err != nil {
		log.Fatal(err)
	}
	os.WriteFile(indexFile, galleryYAML, 0644)

}

func parallelSearch(terms []string, concurrency int, indexFile string) {
	for _, term := range terms {
		scrapeHuggingFace(term, concurrency, indexFile)
	}
}

func main() {
	concurrency := 10
	c := os.Getenv("CONCURRENCY")
	parallelism, err := strconv.Atoi(c)
	if err == nil {
		concurrency = parallelism
	}
	parallelSearch([]string{"TheBloke", "ggml"}, concurrency, indexFile)
}
