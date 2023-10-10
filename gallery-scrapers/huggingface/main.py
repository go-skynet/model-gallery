from huggingface_hub import HfApi, ModelFilter
from pathlib import Path
from typing import List

import multiprocessing
import argparse

from lib.config_recognizer import ConfigRecognizer
from lib.prompt_templating import PromptTemplateCache, PromptTemplateRecognizer
from lib.gallery_scraper import HFGalleryScraper

from config_recognizers.llama import llamaConfigRecognizer, llama2ChatConfigRecognizer

from prompt_recognizers.the_bloke import the_bloke_style





def scraper_process_atrocity_initializer():
    # I am sorry, everyone. This is the best solution I've found. Please send help if you're a real python expert, this can't be the intended method.
    global perProcessClient # Yes, this is a global variable... but if I'm right it's a global that's scoped to each child process - so its more of a singleton than a global
    perProcessClient = HfApi()

# Search Filter Helpers

def build_model_name_search_filter(name: str) -> ModelFilter:
    return ModelFilter(
        model_name=name
    )

##############################
#       MAIN ENTRY POINT
##############################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='HF Gallery Scraper',
                    description='Creates LocalAI Model Galleries for HuggingFace Repos',
                    epilog='©2023 dave@gray101.com and the go-skynet team.')
    
    parser.add_argument("--root", default=Path.cwd(), type=Path)
    parser.add_argument("--count", default=multiprocessing.cpu_count(), type=int)
    parser.add_argument("--downloadRoot", default="https://raw.githubusercontent.com/go-skynet/model-gallery/main/prompt-templates/", type=str)

    args = parser.parse_args()

    configRecognizers: List[ConfigRecognizer] = [
        llama2ChatConfigRecognizer,
        llamaConfigRecognizer
    ]

    prompt_template_recognizers: List[PromptTemplateRecognizer] = [
        the_bloke_style
    ]

    searchFilters: List[ModelFilter] = [
        build_model_name_search_filter("CodeLlama-7B-GGML"),
        # ModelFilter(
        #     author="TheBloke",
        #     task="text-generation"
        # )
    ]

    promptTemplateCache = PromptTemplateCache(args.root / "prompt-templates", args.downloadRoot)

    masterProcessAPI = HfApi()   # TODO: token?

    print(f"=== HuggingFace HF_HUB Scraper ===\n{args}\n\n")

    # First Draft: Do a single search at a time, multi-process the results.
    # This may not be the most efficient or effective strategy when all is said and done, but it will be the simplest to reason about in testing
    # Some possibilities include combining all searches to avoid pool creation overhead... or running pools of pools?
    for filter in searchFilters:
        print(f"Creating a pool of size {args.count} for {filter}")
        pool = multiprocessing.Pool(processes=args.count, initializer=scraper_process_atrocity_initializer)
        searchResultIterator = masterProcessAPI.list_models(filter=filter, cardData=True, full=True, fetch_config=True)

        # Embarrassingly parallel - individual search results are totally independent and are IO bound anyway
        results = pool.imap_unordered(HFGalleryScraper(args.root, configRecognizers, prompt_template_recognizers, promptTemplateCache, None), searchResultIterator)

        for result in results:
            print("Result:", result)

        pool.close()
        pool.join()

