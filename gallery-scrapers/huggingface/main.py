from huggingface_hub import HfApi, ModelFilter
from pathlib import Path
from typing import List, Dict

import multiprocessing
import argparse
import tabulate
import os
import datetime
import tqdm

from lib.base_models import ScrapeResult, ScrapeResultStatus
from lib.config_recognizer import ConfigRecognizer
from lib.prompt_templating import PromptTemplateCache, AutoPromptTemplateConfig
from lib.gallery_scraper import HFGalleryScraper
from lib.utils import purge_folder

from config_recognizers.llama import llamaConfigRecognizer, llama2ChatConfigRecognizer, mistralConfigRecognizer, llamaFallbackConfigRecognizer
from config_recognizers.bert import bertCppConfigRecognizer
from config_recognizers.rwkv import rwkvConfigRecognizer

from prompt_recognizers.the_bloke import the_bloke_style
from prompt_recognizers.rwkv import rwkv_by_tag

def scraper_process_atrocity_initializer():
    # I am sorry, everyone. This is the best solution I've found. Please send help if you're a real python expert, this can't be the intended method.
    global perProcessClient # Yes, this is a global variable... but if I'm right it's a global that's scoped to each child process - so its more of a singleton than a global
    perProcessClient = HfApi()


ALL_CONFIG_RECOGNIZERS: List[ConfigRecognizer] = [
    llama2ChatConfigRecognizer,
    llamaConfigRecognizer,
    mistralConfigRecognizer,
    llamaFallbackConfigRecognizer,
    bertCppConfigRecognizer,
    rwkvConfigRecognizer
]

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
    parser.add_argument("--targetFolder", default="huggingface", type=str)
    parser.add_argument("--downloadRoot", default="https://raw.githubusercontent.com/dave-gray101/model-gallery/main/prompt-templates/", type=str)
    parser.add_argument("--promptTemplateFolder", default="prompt-templates", type=str)
    parser.add_argument("--purgeModels", default=False, type=bool)
    parser.add_argument("--purgeTemplates", default=False, type=bool)

    args = parser.parse_args()

    configRecognizers: List[ConfigRecognizer] = ALL_CONFIG_RECOGNIZERS

    prompt_template_recognizers: List[AutoPromptTemplateConfig] = [
        the_bloke_style,
        rwkv_by_tag
    ]

    searchFilters: List[ModelFilter] = [
        ModelFilter(
            author="gruber",
        ),
        ModelFilter(
            author="TheBloke",
            # task="text-generation"        # Turns out TheBloke forgets this task sometimes for things that should probably have it... so just scrape extra hard I guess
        )
        # RWKV needs work - currently doesn't actually find anything but the python pth files we can't use?
        # ModelFilter(
        #     tags=["rwkv", "text-generation"],
        #     author="BlinkDL"
        # )
    ]

    promptTemplateCache = PromptTemplateCache(args.root / args.promptTemplateFolder, args.downloadRoot, None)

    masterProcessAPI = HfApi()   # TODO: token?

    print(f"=== HuggingFace HF_HUB Scraper ===\n\n{args}\n\n")

    if args.purgeModels:
        purge_folder(args.root / args.targetFolder)

    if args.purgeTemplates:
        purge_folder(args.root / args.promptTemplateFolder)

    # First Draft: Do a single search at a time, multi-process the results.
    # This may not be the most efficient or effective strategy when all is said and done, but it will be the simplest to reason about in testing
    # Some possibilities include combining all searches to avoid pool creation overhead... or running pools of pools?
    

    for filter in searchFilters:
        print(f"Creating a pool of size {args.count} for {filter}")
        pool = multiprocessing.Pool(processes=args.count, initializer=scraper_process_atrocity_initializer)
        try:
            searchResultIterator = masterProcessAPI.list_models(filter=filter, cardData=True, full=True, fetch_config=True)

            # Embarrassingly parallel - individual search results are totally independent and are IO bound anyway
            results = list(tqdm.tqdm(pool.imap_unordered(HFGalleryScraper(args.root, args.targetFolder, configRecognizers, prompt_template_recognizers, promptTemplateCache, None), searchResultIterator)))

            resultTime = datetime.datetime.now()

            # Sort Results by status to produce results data
            categorizedResults: Dict[ScrapeResultStatus, List[ScrapeResult]] = {}
            total = 0
            for k in ScrapeResultStatus:
                categorizedResults[k] = []
            for result in results:
                total = total + 1
                categorizedResults[result.status].append(result)
                
            summaryResults = [["Status", "Count", "More"]]

            for k in ScrapeResultStatus:
                summaryResults.append([k._name_, str(len(categorizedResults[k])), f"[{k._name_}]"])

            summaryResults.append(["Total", str(total), ""])

            markdownResults = f"##Summary of Results for {resultTime}\n{tabulate.tabulate(summaryResults, headers="firstrow", tablefmt="github")}"

            # TEMPORARY: moved this above the full dump due to size limits. Better solution to follow?
            os.environ['GITHUB_STEP_SUMMARY'] = markdownResults

            for k in ScrapeResultStatus:
                groupTableData = [["Name", "Detail"]]
                for r in categorizedResults[k]:
                    groupTableData.append([r.filename, r.message])
                markdownResults = f"{markdownResults}\n##{k._name_}\n{tabulate.tabulate(groupTableData, headers="firstrow", tablefmt="github")}"

            # os.environ['GITHUB_STEP_SUMMARY'] = markdownResults
            print(markdownResults)

            pool.close()
            pool.join()
        except KeyboardInterrupt:
            print("!!!! TERMINATING POOL AND ABORT")
            pool.terminate()
            break

