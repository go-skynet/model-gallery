from pathlib import Path
from typing import List, Dict
from huggingface_hub import HfApi, ModelCard
from huggingface_hub.hf_api import ModelInfo
from ruamel import yaml
from deepmerge import always_merger, conservative_merger

from lib.base_models import GalleryModel, DownloadableFile
from lib.config_recognizer import ConfigRecognizer
from lib.prompt_templating import PromptTemplateRecognizer, PromptTemplateCache


class HFGalleryScraper:
    def __init__(self, root: Path, configRecognizers: List[ConfigRecognizer], promptTemplateRecognizers: List[PromptTemplateRecognizer], promptTemplateCache:PromptTemplateCache, api: HfApi):  
        self.root = root
        self.configRecognizers = configRecognizers
        self.promptTemplateRecognizers = promptTemplateRecognizers
        self.promptTemplateCache:PromptTemplateCache = promptTemplateCache
        self.api = api
    
    def __call__(self, modelInfo: ModelInfo):                              
        hf_config_path = self.root / "huggingface"
        cleaned_model_id = modelInfo.modelId.replace("/", "__")

        # Weird Initializer: This is to grab the global from multiprocessing child process, not where we create the Builder.
        if self.api == None:
            self.api = globals().get('perProcessClient', HfApi())

        config_path = hf_config_path / f"{cleaned_model_id}--{modelInfo.sha}.yaml"
    
        if config_path.exists():
            print(f"Model: {modelInfo.modelId} already scraped for version {modelInfo.sha}\n")
            return
    
        gallery: List[GalleryModel] = []

        # Create new config file!

        print(f"Creating new gallery configuration for {modelInfo.modelId} Version: {modelInfo.sha}")

        activeRecognizers: List[ConfigRecognizer] = []
        for recognizer in self.configRecognizers:
            if recognizer.filter(modelInfo):
                activeRecognizers.append(recognizer)
            
        if len(activeRecognizers) == 0:
            print(f"No matching config recognizers for {modelInfo.modelId}")
            return

        repoInfo = self.api.repo_info(modelInfo.modelId, files_metadata=True)

        for cr in activeRecognizers:
            modelRepoBaseConfig = cr.perRepo(modelInfo)

            if cr.autoPromptEndpoints != None and len(cr.autoPromptEndpoints) > 0:

                print(f'beginning auto prompting for {modelInfo.modelId}')

                activePromptTemplateRecognizers: List[PromptTemplateRecognizer] = []
                for pRecognizer in self.promptTemplateRecognizers:
                    if pRecognizer.filter(modelInfo):
                        activePromptTemplateRecognizers.append(pRecognizer)

                if len(activePromptTemplateRecognizers) > 0:
                    card = ModelCard.load(modelInfo.modelId)

                    for aPRecognizer in activePromptTemplateRecognizers:
                        promptTemplateResults = aPRecognizer.recognizePrompt(modelInfo, card, modelRepoBaseConfig)
                        if promptTemplateResults != None:
                            promptTemplateResults = aPRecognizer.adaptPrompt(promptTemplateResults, modelInfo, card, modelRepoBaseConfig)
                            promptTemplateFile = self.promptTemplateCache.get_downloadable_file(promptTemplateResults)
                            aptDict: Dict[str, str] = {}
                            for endpoint in cr.autoPromptEndpoints:
                                aptDict[endpoint] = f"{promptTemplateResults.templateName}.tmpl"

                            modelRepoBaseConfig.files.append(promptTemplateFile)
                            modelRepoBaseConfig.config_file = conservative_merger.merge(modelRepoBaseConfig.config_file, {
                                "template": aptDict
                            })
                            

            for repoFile in repoInfo.siblings:
                baseConfig = cr.perFile(modelInfo, repoFile, modelRepoBaseConfig)

                if baseConfig == None:
                    continue # None here indicates that this repo file should be skipped.

                # Kinda a hack, copy base to file-specific so we don't drag every one along in the loop via append
                fileSpecificFiles =  baseConfig.files.copy()
                fileSpecificFiles.append(DownloadableFile(
                    Filename=repoFile.rfilename,
                    SHA256=repoFile.lfs["sha256"],
                    URI=f"https://huggingface.co/{modelInfo.modelId}/resolve/main/{repoFile.rfilename}"
                ))

                # TODO: This is a first draft. Improvements to follow
                galleryModel: GalleryModel = GalleryModel(
                    name=f"{modelInfo.modelId.replace("/", "__")}__{repoFile.rfilename}",
                    urls=[f"https://huggingface.co/{modelInfo.modelId}"],
                    config_file= always_merger.merge(baseConfig.config_file.copy(), {
                        "parameters": {
                            "model": repoFile.rfilename
                        }
                    }),
                    # url= baseConfig.path,
                    files=fileSpecificFiles,
                    tags=modelInfo.tags,
                    icon="https://huggingface.co/front/assets/huggingface_logo-noborder.svg", # :D
                    license=modelInfo.cardData["license"],
                    description=f"{modelInfo.modelId} - {cr.id} configuration"
                )
                gallery.append(galleryModel)

        # Eggregious Stack Overflow Hack: https://stackoverflow.com/questions/48813495/pyyaml-dump-python-object-without-tags
        yaml.emitter.Emitter.process_tag = lambda self, *args, **kw: None
        # Another one too... mypy hates these.
        yaml.Representer.ignore_aliases = lambda self, *args, **kw: True

        # dump that file we checked for at the very start
        with open(config_path, 'x') as configFile:
            yaml.dump(gallery, configFile, default_flow_style=False, explicit_start=True)

        # update the SHAless symlink
        Path( hf_config_path / f"{cleaned_model_id}.yaml").symlink_to(config_path)
