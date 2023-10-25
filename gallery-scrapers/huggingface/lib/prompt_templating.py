from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Set, Optional, Tuple
from urllib.parse import urljoin
from huggingface_hub import ModelCard
from huggingface_hub.hf_api import ModelInfo
from mistletoe import Document, ast_renderer
from multiprocessing import Lock

from lib.base_models import BaseConfigData, DownloadableFile, LocalAIEndpoints
from lib.config_recognizer import ModelInfoFilterFunctionType, ConfigRecognizer, neverModelInfoFilter, nopConfigRecognizerPerFileFn

import regex
import hashlib

promptTemplateCacheLock = Lock()

class PromptTemplateRecognizerResult:
    def __init__(self, templateName: str, templateBody: str):
        self.templateName = templateName
        self.templateBody = templateBody

PromptTemplateRecognizerFilterFn = Callable[[ModelInfo], bool]
PromptTemplateRecognizerFn = Callable[[ModelInfo, ModelCard, BaseConfigData], Optional[PromptTemplateRecognizerResult]]
PromptTemplateAdapterFn = Callable[[PromptTemplateRecognizerResult, ModelInfo, ModelCard, BaseConfigData], Optional[Tuple[PromptTemplateRecognizerResult, BaseConfigData]]]

def nopAdapterFn(orig):
    return orig

class PromptTemplateRecognizer:
    def __init__(self, id: str, filter: PromptTemplateRecognizerFilterFn, recognizePrompt: PromptTemplateRecognizerFn, adaptPrompt: PromptTemplateAdapterFn, permittedEndpoints: Set[LocalAIEndpoints]):
        self.id = id
        self.filter = filter or neverModelInfoFilter    # Close Enough since it's just lambda: false
        self.recognizePrompt = recognizePrompt or nopConfigRecognizerPerFileFn
        self.adaptPrompt = adaptPrompt or nopAdapterFn
        self.permittedEndpoints= permittedEndpoints or set()    # If this isn't overriden, fail to replace anything for safety.

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
    return None            

# NOTE: fixedTitle last, experimentally partial the partial for name binding?
def header_regex_prompt_recognizer(tokenType: str, childDistance: int, substitutionTests: Dict[str,str], fixedTitle: str, _: ModelInfo, modelCard: ModelCard, __:BaseConfigData):
    ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
    if ast != None and ast['children'] != None:
        for i in range(len(ast['children'])):
            c = ast['children'][i]
            if c["type"] == tokenType:
                c2content = c["children"][childDistance]['content']
                for k in substitutionTests.keys():
                    m = regex.match(k, c2content)
                    if m != None:
                        return PromptTemplateRecognizerResult(fixedTitle, c2content)

    return None
                    

def fixed_title_top_level_type_prompt_recognizer(fixedTitle: str, tokenType: str, matchOffset: int, _: ModelInfo, modelCard: ModelCard, __:BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
    if ast != None and ast['children'] != None:
        # weirdly manual loop is because some versions of this code cared about absolute indexes, and I'm still not sure that combining both of these together isn't the right idea
        countOffset = 0
        for i in range(len(ast['children'])):
            c = ast['children'][i]
            if c["type"] == tokenType:
                if matchOffset == countOffset:
                    return PromptTemplateRecognizerResult(fixedTitle, c["children"][0]['content'])
                countOffset = countOffset + 1

    return None

def prompt_template_name_model_id_brander(fixedPrefix: str, modelInfo: ModelInfo, _: ModelCard, __:BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    return PromptTemplateRecognizerResult(templateName=f"{fixedPrefix}{modelInfo.modelId.split('/')[:-1]}")

def split_prompt_recognizer(nameRecognizer: PromptTemplateRecognizerFn, bodyRecognizer: PromptTemplateRecognizerFn, modelInfo: ModelInfo, modelCard: ModelCard, baseConfigData:BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    return PromptTemplateRecognizerResult(
        templateName=nameRecognizer(modelInfo, modelCard, baseConfigData).templateName,
        templateBody=bodyRecognizer(modelInfo, modelCard, baseConfigData).templateBody,
    )

__adapt_prompt_template_variable_names_default_substitutions = {
    r"{prompt}": r"{{.Input}}"
}

def adapt_prompt_template_simple_replace_variable_names(substitutions: Dict[str,str], promptTemplateResult: PromptTemplateRecognizerResult, modelInfo: ModelInfo, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    for k, v in substitutions.items():
        promptTemplateResult.templateBody = promptTemplateResult.templateBody.replace(k, v)

    return (promptTemplateResult, baseConfigData)

adapt_prompt_template_simple_defaults_replacements = partial(adapt_prompt_template_simple_replace_variable_names, __adapt_prompt_template_variable_names_default_substitutions)

def adapt_prompt_template_regex_replace_variable_names(substitutions: Dict[str,str], promptTemplateResult: PromptTemplateRecognizerResult, modelInfo: ModelInfo, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    for k, v in substitutions.items():
        promptTemplateResult.templateBody = regex.sub(k, v, promptTemplateResult.templateBody)

    return (promptTemplateResult, baseConfigData)

def adapt_prompt_template_fixed_value(promptTemplateResult: PromptTemplateRecognizerResult, _: PromptTemplateRecognizerResult, modelInfo: ModelInfo, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    return (promptTemplateResult, baseConfigData)

# Not totally sure this is the right place to be doing this... but for v1 it'll work.
def adapt_prompt_template_extract_roles(roleRegex: str, promptTemplateResult: PromptTemplateRecognizerResult, modelInfo: ModelInfo, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:

    foundRoles: List[str] = []
    for line in promptTemplateResult.templateBody.splitlines():
        roleMatch = regex.match(roleRegex, line)
        if roleMatch and len(roleMatch.groups()) > 1:
            if bool(foundRoles.index(roleMatch.group(1))):
                foundRoles.append(roleMatch.group(1))

    # TODO: probably make this pluggable. For now, use a horrible hack to map based on order :D
    baseConfigData.config_file["roles"] = baseConfigData.config_file.get("roles", {})
    for rI in range(0, min(len(foundRoles), 2)):
        match rI:
            case 0:
                baseConfigData.config_file["roles"]["user"] = foundRoles[rI]
            case 1:
                baseConfigData.config_file["roles"]["assistant"] = foundRoles[rI]
            case 2:
                baseConfigData.config_file["roles"]["system"] = foundRoles[rI]

    return (promptTemplateResult, baseConfigData)

adapt_prompt_template_extract_roles_simple = partial(adapt_prompt_template_extract_roles, r"(.*):")

def create_fixed_prompt_template_recognizer(id: str, filter: ModelInfoFilterFunctionType, result: PromptTemplateRecognizerResult) -> PromptTemplateRecognizer:
    return PromptTemplateRecognizer(id, filter, nopConfigRecognizerPerFileFn, partial(adapt_prompt_template_fixed_value(result)))

class PromptTemplateCache:
    def __init__(self, templateRoot: Path, downloadRoot: str):
        self.templateRoot = templateRoot
        self.downloadRoot = downloadRoot
        self.downloadableFileCache: Dict[str, DownloadableFile] = {}

    def get_prompt_template_directory_path(self) -> Path:
        return self.templateRoot

    def write_prompt_template_to_file(self, outputPath: Path, template: str):
        with open(outputPath, 'x') as outputFile:
            outputFile.writelines(template)

    def get_prompt_path(self, promptTemplateResult: PromptTemplateRecognizerResult) -> Path:
        promptTemplatePath = self.templateRoot / f"{promptTemplateResult.templateName}.tmpl"      
        if promptTemplatePath.exists():
            # TODO: Consider checking how different it is from the text match, since we already have the text body?
            # For now, always trust that the file is better than the regex, since it might be hand-edited.
            # print(f'Existing prompt template path {promptTemplatePath} already exists!')
            return promptTemplatePath
        try:
            self.write_prompt_template_to_file(promptTemplatePath, promptTemplateResult.templateBody)
            return promptTemplatePath
        except:
            return None
        
    def get_downloadable_file(self, promptTemplateResult: PromptTemplateRecognizerResult) -> DownloadableFile:
        
        if promptTemplateResult.templateName in self.downloadableFileCache:
            # print(f"prompt template found in cache: {promptTemplateResult.templateName}")
            return self.downloadableFileCache[promptTemplateResult.templateName]
        
        # print(f"automatic prompt template caching started for {promptTemplateResult.templateName}")

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
        return df
    