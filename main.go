package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type Model struct {
	ModelID string `json:"modelId"`
	Author  string `json:"author"`
}

type ModelFiles struct {
	Siblings []Sibling `json:"siblings"`
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

	// Step 2: Process each model and retrieve its files (siblings)
	for _, model := range modelList {
		fmt.Println("Model ID:", model.ModelID)

		// Step 3: Retrieve model files (siblings)
		modelFiles, err := getModelFiles(model.ModelID)
		if err != nil {
			log.Println("Failed to retrieve files for model", model.ModelID)
			continue
		}

		// Step 4: Save the model files
		err = saveModelFiles(model.ModelID, modelFiles)
		if err != nil {
			log.Println("Failed to save files for model", model.ModelID)
			continue
		}

		fmt.Println("Files saved for model", model.ModelID)
		fmt.Println()
	}
}

func getModelFiles(modelID string) (ModelFiles, error) {
	var files ModelFiles

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

func getETag(url string) (string, error) {
	resp, err := http.Head(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	etag := resp.Header.Get("ETag")
	return etag, nil
}
func getETagSHA256(url string) (string, error) {
	resp, err := http.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	// Compute SHA256 hash of the response body
	hash := sha256.New()
	if _, err := io.Copy(hash, resp.Body); err != nil {
		return "", err
	}
	etag := fmt.Sprintf("%x", hash.Sum(nil))

	return etag, nil
}

func saveModelFiles(modelID string, modelFiles ModelFiles) error {
	for _, sibling := range modelFiles.Siblings {
		if !strings.HasSuffix(sibling.RFileName, ".bin") {
			fmt.Println("not a bin ", sibling.RFileName)

			continue
		}
		if strings.HasPrefix(sibling.RFileName, "pytorch") {
			fmt.Println("pythorch", sibling.RFileName)

			continue
		}
		fileURL := fmt.Sprintf("https://huggingface.co/models/%s/raw/main/%s", modelID, sibling.RFileName)

		etag, err := getETag(fileURL)
		if err != nil {

			fmt.Println("Failed to get etag", sibling.RFileName, err)
			continue
		}

		fmt.Println("Saving file", sibling.RFileName, etag)

		continue
		// Retrieve the sibling file
		resp, err := http.Get(fmt.Sprintf("https://huggingface.co/models/%s/raw/main/%s", modelID, sibling.RFileName))
		if err != nil {
			return err
		}
		defer resp.Body.Close()

		// Create the directory to save the files if it doesn't exist
		err = os.MkdirAll(modelID, os.ModePerm)
		if err != nil {
			return err
		}

		// Create the file
		filePath := filepath.Join(modelID, sibling.RFileName)
		file, err := os.Create(filePath)
		if err != nil {
			return err
		}
		defer file.Close()

		// Save the file content
		_, err = io.Copy(file, resp.Body)
		if err != nil {
			return err
		}
	}

	return nil
}
