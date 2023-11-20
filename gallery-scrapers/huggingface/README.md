# HuggingFace to LocalAI Configuration Scraper

This tool is intended to be used to generate best-effort LocalAI model configuration and prompt templating files automatically for models hosted on huggingface.com

Documentation is currently very incomplete, but here's some quick notes:

`main.py` in this directory is the entrypoint for the multiprocess master script. It is responsible for kicking off all child processes that actually handle the scraping and config file writing.

The `lib` directory holds the code that implements this scraping / conversion. This should only need to be edited if you like python and want to help improve the scraper or fix bugs

The `prompt_recognizers` directory currently only has a single known-working format in it, which is the one used by the model cards of prolific model converter TheBloke. Currently it comes in a strict form that actually checks its one of his, and a "style of" form that doesn't enforce any filtering. Please add more formats here if your model card uses a different style!

The `config_recognizers` directory has more to it, but is similarly incomplete. Files here are responsible for identifying the different model types used on huggingface, so please look at the examples in here and add more as new models come out every day.


### Dave's Junk Drawer
Not currently needed but it may come back.
```
def load_yaml_file_to_config(path: Path):
    with open(path, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ValueError("invalid path")
```