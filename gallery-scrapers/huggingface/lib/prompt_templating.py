from typing import Callable, Dict, Optional
from pathlib import Path
from urllib.parse import urljoin
from huggingface_hub import ModelCard
from huggingface_hub.hf_api import ModelInfo
from mistletoe import Document, ast_renderer
from multiprocessing import Lock

from lib.base_models import BaseConfigData, DownloadableFile
from lib.config_recognizer import ModelInfoFilterFunctionType, neverModelInfoFilter, nopConfigRecognizerPerFileFn

import regex
import random
import hashlib

promptTemplateCacheLock = Lock()

class PromptTemplateRecognizerResult:
    def __init__(self, templateName: str, templateBody: str):
        self.templateName = templateName
        self.templateBody = templateBody

PromptTemplateRecognizerFn = Callable[[ModelInfo, ModelCard, BaseConfigData], Optional[PromptTemplateRecognizerResult]]
PromptTemplateAdapterFn = Callable[[PromptTemplateRecognizerResult, ModelInfo, ModelCard, BaseConfigData], Optional[PromptTemplateRecognizerResult]]

def nopAdapterFn(orig):
    return orig

class PromptTemplateRecognizer:
    def __init__(self, id: str, filter: ModelInfoFilterFunctionType, recognizePrompt: PromptTemplateRecognizerFn, adaptPrompt: PromptTemplateAdapterFn):
        self.id = id
        self.filter = filter or neverModelInfoFilter
        self.recognizePrompt = recognizePrompt or nopConfigRecognizerPerFileFn
        self.adaptPrompt = adaptPrompt or nopAdapterFn


def header_offset_prompt_recognizer(headingLevel: int, headingRegex: str, offset: int, _: ModelInfo, modelCard: ModelCard, __:BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
    if ast != None and ast['children'] != None:
        for i in range(len(ast['children'])):
            c = ast['children'][i]
            if c['type'] == 'Heading' and c['level'] == headingLevel:
                c2 = c['children'][0]
                if c2['type'] == 'RawText':
                    rm = regex.match(headingRegex, c2['content'])
                    if rm != None:
                        promptTitle = rm.group(1)
                        if len(promptTitle) > 0:
                            return PromptTemplateRecognizerResult(promptTitle, ast['children'][i + offset]['children'][0]['content'])
                

def adapt_prompt_template_variable_names(promptTemplateResult: PromptTemplateRecognizerResult, modelInfo: ModelInfo, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    substitutions = {
        r"{prompt}": r"{{.Input}}"
    }

    for k, v in substitutions.items():
        promptTemplateResult.templateBody = promptTemplateResult.templateBody.replace(k, v)

    return promptTemplateResult

class PromptTemplateCache:
    def __init__(self, templateRoot: Path, downloadRoot: str):
        self.templateRoot = templateRoot
        self.downloadRoot = downloadRoot
        self.downloadableFileCache: Dict[str, DownloadableFile] = {}
        self.id = random.random()   # TODO CLEANUP, FOR INIT TESTING

    def __str__(self):
        return f"[PromptTemplateCache {self.id}]\ntemplateRoot: {self.templateRoot}\ndownloadRoot: {self.downloadRoot}\ncached entries: {"\n".join(self.downloadableFileCache.keys())}"

    def write_prompt_template_to_file(self, outputPath: Path, template: str):
        with open(outputPath, 'x') as outputFile:
            outputFile.writelines(template)

    def get_prompt_path(self, promptTemplateResult: PromptTemplateRecognizerResult) -> Path:
        promptTemplatePath = self.templateRoot / f"{promptTemplateResult.templateName}.tmpl"      
        if promptTemplatePath.exists():
            # TODO: Consider checking how different it is from the text match, since we already have the text body?
            # For now, always trust that the file is better than the regex, since it might be hand-edited.
            print(f'Existing prompt template path {promptTemplatePath} already exists!')
            return promptTemplatePath
        try:
            self.write_prompt_template_to_file(promptTemplatePath, promptTemplateResult.templateBody)
            return promptTemplatePath
        except:
            return None
        
    def get_downloadable_file(self, promptTemplateResult: PromptTemplateRecognizerResult) -> DownloadableFile:
        
        if promptTemplateResult.templateName in self.downloadableFileCache:
            print(f"prompt template found in cache: {promptTemplateResult.templateName}")
            return self.downloadableFileCache[promptTemplateResult.templateName]
        
        print(f"automatic prompt template caching started for {promptTemplateResult.templateName}")

        promptTemplateCacheLock.acquire()
        pp = self.get_prompt_path(promptTemplateResult)
        sha256:str = None
        with open(pp, "rb") as f:
            sha256 = hashlib.file_digest(f, "sha256").hexdigest()

        df = DownloadableFile(
            Filename=f"{promptTemplateResult.templateName}.tmpl",
            SHA256=sha256,
            URI=urljoin(self.downloadRoot, f"{promptTemplateResult.templateName}.tmpl")
        )
        self.downloadableFileCache[promptTemplateResult.templateName] = df
        promptTemplateCacheLock.release()
        # print(self)
        return df
