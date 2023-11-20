<h1 align="center">
  <br>
  <img height="300" src="https://github.com/go-skynet/model-gallery/assets/2420543/7a6a8183-6d0a-4dc4-8e1d-f2672fab354e"> <br>
  <a href="https://github.com/go-skynet/LocalAI">LocalAI</a> model gallery
<br>
</h1>

The model gallery is an automatically updated collection of model and prompt configurations for the community of users of [LocalAI](https://github.com/go-skynet/LocalAI).

Please note that entries in this repository are generated automatically and may not always be correct! We encourage contributions to the gallery to correct these issues!

## Suggestions
While this scraper is automated, there is effort required to support new model card formats and to recognize different configurations. If a model you are interested in running is available on HuggingFace, but does not appear within this gallery, please submit a PR to create a new `config_recognizer` for it. Nontechnical users should create an issue on this repo, rather than LocalAI - if the missing models are interesting enough, someone will implement the recognizer.

## Helper tool

To load a model from main onto localhost

```shell
bash ./load.sh wizard
```

## HuggingFace Scraper
For more info about the new python-based HuggingFace scraper used to generate best-effort model galleries, see the [dedicated README file](/gallery-scrapers/huggingface/README.md)

## Using the Model Gallery 
For how to use the files in this repository, see the [Documentation](https://localai.io/models/). This may not be updated yet...
