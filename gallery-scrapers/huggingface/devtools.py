
import argparse

from pathlib import Path
from mistletoe import Document, ast_renderer
from huggingface_hub import ModelCard, HfApi

from lib.utils import purge_folder, json_dump

from main import ALL_CONFIG_RECOGNIZERS

##############################
#       MAIN ENTRY POINT
##############################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='HF Gallery Scraper Developer Tools',
                    description='This is not the scraper, only developers need to use this script',
                    epilog='©2023 dave@gray101.com and the go-skynet team.')
    
    parser.add_argument("--root", default=Path.cwd(), type=Path)
    parser.add_argument("--purgeModels", default=False, type=bool)
    parser.add_argument("--purgeTemplates", default=False, type=bool)
    parser.add_argument("--purgeDevDumps", default=False, type=bool)
    parser.add_argument("--dumpCardAST", default="", type=str)
    parser.add_argument("--dumpModelInfo", default="", type=str)
    parser.add_argument("--testCR", default="", type=str)

    args = parser.parse_args()

    print(f"=== HuggingFace Scraper Dev Tools ===\n{args}\n\n")

    ddModelInfo = args.root / "dev-dumps" /  "modelInfo"
    ddAst = args.root / "dev-dumps" / "ast" 

    if args.purgeModels:
        purge_folder(args.root / args.targetFolder)

    if args.purgeTemplates:
        purge_folder(args.root / args.promptTemplateFolder)

    if args.purgeDevDumps:
        purge_folder(ddModelInfo)
        purge_folder(ddAst)

    if len(args.dumpModelInfo) > 0:
        api = HfApi()
        modelInfo = api.model_info(args.dumpModelInfo)
        path = ddModelInfo / f"{args.dumpModelInfo}.json"
        json_dump(path, {
            "modelId": modelInfo.modelId,
            "author": modelInfo.author,
            "config": modelInfo.config,
            "lastModified": modelInfo.lastModified,
            "sha": modelInfo.sha,
            "tags": modelInfo.tags
        })

    if len(args.dumpCardAST) > 0:
        modelCard = ModelCard.load(args.dumpCardAST)
        ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
        path = ddAst / f"{args.dumpCardAST}.json"
        json_dump(path, ast)

    if len(args.testCR) > 0:
        print(f"Testing Config Recognizer matches for {args.testCR}...")
        api = HfApi()
        modelInfo = api.model_info(args.testCR)
        for cr in ALL_CONFIG_RECOGNIZERS:
            if cr.filter(modelInfo):
                print(f"Filter passes for {cr.id}")