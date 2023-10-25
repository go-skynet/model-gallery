import os
import datetime

from pathlib import Path
from typing import List, Dict
from huggingface_hub import HfApi, ModelCard
from huggingface_hub.hf_api import ModelInfo
from ruamel import yaml
from deepmerge import always_merger, conservative_merger

from lib.base_models import GalleryModel, DownloadableFile, ScrapeResult, ScrapeResultStatus
from lib.config_recognizer import ConfigRecognizer
from lib.prompt_templating import PromptTemplateRecognizer, PromptTemplateCache


class HFGalleryScraper:
    def __init__(self, root: Path, targetFolder: str, configRecognizers: List[ConfigRecognizer], promptTemplateRecognizers: List[PromptTemplateRecognizer], promptTemplateCache:PromptTemplateCache, api: HfApi):  
        self.root = root
        self.targetFolder = targetFolder
        self.configRecognizers = configRecognizers
        self.promptTemplateRecognizers = promptTemplateRecognizers
        self.promptTemplateCache:PromptTemplateCache = promptTemplateCache
        self.api = api
    
    def __call__(self, modelInfo: ModelInfo):                              
        hf_config_path = self.root / self.targetFolder
        cleaned_model_id = modelInfo.modelId.replace("/", "__")

        # Weird Initializer: This is to grab the global from multiprocessing child process, not where we create the Builder.
        if self.api == None:
            self.api = globals().get('perProcessClient', HfApi())

        output_filename = f"{cleaned_model_id}--{modelInfo.sha}.yaml"

        config_path = hf_config_path / output_filename
    
        if config_path.exists():
            return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.UNCHANGED, message=str(datetime.datetime.now()))
    
        gallery: List[GalleryModel] = []

        # Create new config file!
        # print(f"Creating new gallery configuration for {modelInfo.modelId} Version: {modelInfo.sha}")

        activeRecognizers: List[ConfigRecognizer] = []
        for recognizer in self.configRecognizers:
            if recognizer.filter(modelInfo):
                activeRecognizers.append(recognizer)
            
        if len(activeRecognizers) == 0:
            return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.ERROR, message=f"No matching config recognizers for {modelInfo.modelId}")

        try:
            repoInfo = self.api.repo_info(modelInfo.modelId, files_metadata=True)

            for cr in activeRecognizers:
                modelRepoBaseConfig = cr.perRepo(modelInfo)
                # print(f'Creating a config using {cr.id} for {modelInfo.modelId}')
                if cr.autoPromptEndpoints != None and len(cr.autoPromptEndpoints) > 0:

                    # print(f'beginning auto prompting for {modelInfo.modelId}')

                    activePromptTemplateRecognizers: List[PromptTemplateRecognizer] = []
                    for pRecognizer in self.promptTemplateRecognizers:
                        if pRecognizer.filter(modelInfo):
                            activePromptTemplateRecognizers.append(pRecognizer)

                    if len(activePromptTemplateRecognizers) > 0:
                        card = ModelCard.load(modelInfo.modelId)

                        for aPRecognizer in activePromptTemplateRecognizers:
                            promptTemplateResults = aPRecognizer.recognizePrompt(modelInfo, card, modelRepoBaseConfig)
                            if promptTemplateResults != None:
                                (promptTemplateResults, modelRepoBaseConfig) = aPRecognizer.adaptPrompt(promptTemplateResults, modelInfo, card, modelRepoBaseConfig)
                                promptTemplateFile = self.promptTemplateCache.get_downloadable_file(promptTemplateResults)
                                aptDict: Dict[str, str] = {}
                                for endpoint in cr.autoPromptEndpoints.intersection(aPRecognizer.permittedEndpoints):
                                    aptDict[endpoint.value] = promptTemplateResults.templateName # f"{promptTemplateResults.templateName}.tmpl"

                                modelRepoBaseConfig.files.append(promptTemplateFile)
                                modelRepoBaseConfig.config_file = conservative_merger.merge(modelRepoBaseConfig.config_file, {
                                    "template": aptDict
                                })
                    else:
                        print("WARNING: Active Prompt Template Recognition has failed, attempting fallback to existing templates")
                        tempPTDict = {}
                        # Fallback: No matching prompt recognizers for this config, but we have holes to fill.
                        # This code is not efficient, but checks for file name based matches.
                        for de in os.scandir(self.promptTemplateCache.get_prompt_template_directory_path()):
                            if de.is_file() and de.name.endswith(".tmpl"):
                                templateName = de.name[:-5]
                                if bool(modelInfo.modelId.index(templateName)):
                                    for ep in cr.autoPromptEndpoints:
                                        if templateName[:(-1 - len(ep.value))] == f"-{ep.value}":
                                            tempPTDict[ep.value] = templateName

                                    for mEp in cr.autoPromptEndpoints.difference(tempPTDict.keys()):
                                        tempPTDict[mEp.value] = templateName

                            modelRepoBaseConfig.config_file = conservative_merger.merge(modelRepoBaseConfig.config_file, {
                                "template": tempPTDict
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
                        name=f"{cleaned_model_id}__{repoFile.rfilename}",
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

            if len(gallery) == 0:
                return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.EMPTY)
            
            # Eggregious Stack Overflow Hack: https://stackoverflow.com/questions/48813495/pyyaml-dump-python-object-without-tags
            yaml.emitter.Emitter.process_tag = lambda self, *args, **kw: None
            # Another one too... mypy hates these.
            yaml.Representer.ignore_aliases = lambda self, *args, **kw: True

            # dump that file we checked for at the very start
            with open(config_path, 'x') as configFile:
                yaml.dump(gallery, configFile, default_flow_style=False, explicit_start=False)

            # update the reference file - a symlink to a file within a temporary builder action isn't very useful, so create this link instead which we can follow on the LocalAI side.
            with open(Path(hf_config_path / f"{cleaned_model_id}.ref"), 'w') as referenceFile:
                referenceFile.write(output_filename)

            return ScrapeResult(filename=output_filename, gallery=gallery, status = ScrapeResultStatus.SUCCESS, message=f"Created with {len(gallery)} models")
        
        except Exception as error:
            return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.ERROR, message=str(error))
