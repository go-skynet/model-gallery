import os
import datetime

from pathlib import Path
from typing import List, Dict
from huggingface_hub import HfApi, ModelCard
from huggingface_hub.hf_api import ModelInfo
from ruamel import yaml
from deepmerge import always_merger, conservative_merger

from lib.base_models import GalleryModel, DownloadableFile, ScrapeResult, ScrapeResultStatus, BaseConfigData
from lib.config_recognizer import ConfigRecognizer
from lib.prompt_templating import AutoPromptTemplateConfig, PromptTemplateCache


class HFGalleryScraper:
    def __init__(self, root: Path, targetFolder: str, configRecognizers: List[ConfigRecognizer], autoPromptTemplateConfigs: List[AutoPromptTemplateConfig], promptTemplateCache:PromptTemplateCache, api: HfApi):  
        self.root = root
        self.targetFolder = targetFolder
        self.configRecognizers = sorted(configRecognizers, key=lambda x: x.priority, reverse=True)
        self.autoPromptTemplateConfigs = autoPromptTemplateConfigs
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

        ### Filter the list of ConfigRecognizers by their filter function down to only the related ones
        activeRecognizers: List[ConfigRecognizer] = []
        for recognizer in self.configRecognizers:
            if recognizer.filter(modelInfo):
                activeRecognizers.append(recognizer)
            if len(activeRecognizers) > 0 and activeRecognizers[0].priority > recognizer.priority:
                # If we have at found at least one recognizer, and we have left that priority rank, we can abort here.
                break
            
        if len(activeRecognizers) == 0:
            ## Abort if nothing matches - specific error message
            return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.ERROR, message=f"No matching config recognizers for {modelInfo.modelId}")

        try:
            repoInfo = self.api.repo_info(modelInfo.modelId, files_metadata=True)

            for cr in activeRecognizers:
                modelRepoBaseConfig = cr.perRepo(modelInfo)
                # print(f'Creating a config using {cr.id} for {modelInfo.modelId}')

                ### AUTOMATIC PROMPT TEMPLATE GENERATION
                if cr.autoPromptEndpoints is not None and len(cr.autoPromptEndpoints) > 0:

                    # print(f'beginning auto prompting for {modelInfo.modelId}')

                    activeAutoPromptTemplateConfigs: List[AutoPromptTemplateConfig] = []
                    for aptc in self.autoPromptTemplateConfigs:
                        if aptc.filter(modelInfo):
                            activeAutoPromptTemplateConfigs.append(aptc)

                    if len(activeAutoPromptTemplateConfigs) > 0:
                        card = ModelCard.load(modelInfo.modelId)

                        for autoPromptTemplateRecognizer in activeAutoPromptTemplateConfigs:
                            promptTemplateResults = autoPromptTemplateRecognizer.extractPrompt(modelInfo, card, modelRepoBaseConfig)
                            if promptTemplateResults is not None:
                                bundle = autoPromptTemplateRecognizer.adaptPrompt(promptTemplateResults, card, modelRepoBaseConfig)
                                if bundle is not None:
                                    promptTemplateResults = bundle.result
                                    modelRepoBaseConfig = bundle.config

                                promptTemplateFile = self.promptTemplateCache.get_downloadable_file(promptTemplateResults)
                                if promptTemplateFile is not None:
                                    aptDict: Dict[str, str] = {}
                                    for endpoint in cr.autoPromptEndpoints.intersection(autoPromptTemplateRecognizer.permittedEndpoints):
                                        aptDict[endpoint.value] = promptTemplateResults.templateName # f"{promptTemplateResults.templateName}.tmpl"

                                    modelRepoBaseConfig.files.append(promptTemplateFile)
                                    modelRepoBaseConfig.config_file = conservative_merger.merge(modelRepoBaseConfig.config_file, {
                                        "template": aptDict
                                    })
                                else:
                                    self.__fallbackAutoPromptTemplate(modelInfo, cr, modelRepoBaseConfig)
                    else:
                        self.__fallbackAutoPromptTemplate(modelInfo, cr, modelRepoBaseConfig)

                for repoFile in repoInfo.siblings:
                    baseConfig = cr.perFile(modelInfo, repoFile, modelRepoBaseConfig)

                    if baseConfig is None:
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


            #### OUTPUT SECTION: CODE BELOW HERE IS FOR WRITING OUT THE RESULTS

            if len(gallery) == 0:
                return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.EMPTY)
            
            # Eggregious Stack Overflow Hack: https://stackoverflow.com/questions/48813495/pyyaml-dump-python-object-without-tags
            yaml.emitter.Emitter.process_tag = lambda self, *args, **kw: None   # type: ignore
            # Another one too... mypy hates these.
            yaml.Representer.ignore_aliases = lambda self, *args, **kw: True    # type: ignore

            # dump that file we checked for at the very start
            with open(config_path, 'x') as configFile:
                yaml.dump(gallery, configFile, default_flow_style=False, explicit_start=False)

            # update the reference file - a symlink to a file within a temporary builder action isn't very useful, so create this link instead which we can follow on the LocalAI side.
            with open(Path(hf_config_path / f"{cleaned_model_id}.ref"), 'w') as referenceFile:
                referenceFile.write(output_filename)

            return ScrapeResult(filename=output_filename, gallery=gallery, status = ScrapeResultStatus.SUCCESS, message=f"Created with {len(gallery)} models")
        
        except Exception as error:
            return ScrapeResult(filename=output_filename, gallery=[], status=ScrapeResultStatus.ERROR, message=str(error))

    def __fallbackAutoPromptTemplate(self, modelInfo: ModelInfo, configRecognizer: ConfigRecognizer, modelRepoBaseConfig: BaseConfigData) -> BaseConfigData:
        print("WARNING: Active Prompt Template Recognition has failed, attempting fallback to existing templates")
        tempPTDict = {}
        # Fallback: No matching prompt recognizers for this config, but we have holes to fill.
        # This code is not efficient, but checks for file name based matches.
        for de in os.scandir(self.promptTemplateCache.get_prompt_template_directory_path()):
            if de.is_file() and de.name.endswith(".tmpl"):
                templateName = de.name[:-5]
                if bool(modelInfo.modelId.index(templateName)):
                    for ep in configRecognizer.autoPromptEndpoints:
                        if templateName[:(-1 - len(ep.value))] == f"-{ep.value}":
                            tempPTDict[ep.value] = templateName

                    for mEp in configRecognizer.autoPromptEndpoints.difference(tempPTDict.keys()):
                        tempPTDict[mEp.value] = templateName

            modelRepoBaseConfig.config_file = conservative_merger.merge(modelRepoBaseConfig.config_file, {
                "template": tempPTDict
            })

            return modelRepoBaseConfig