from typing import Callable, Dict, Optional
from functools import partial
from huggingface_hub import ModelCard
from huggingface_hub.hf_api import ModelInfo
from mistletoe import Document, ast_renderer

import regex

from lib.base_models import BaseConfigData

from .result import AutomaticPromptTemplateResult

PromptTemplateExtractorFn = Callable[[ModelInfo, ModelCard, BaseConfigData], Optional[AutomaticPromptTemplateResult]]

###

def __nopPromptTemplateExtractor(modelInfo: ModelInfo, _: ModelCard, __: BaseConfigData) -> Optional[AutomaticPromptTemplateResult]:
    return AutomaticPromptTemplateResult(
        modelInfo=modelInfo,
        templateName="",
        templateBody=""
    )

_nopPromptTemplateExtractor: PromptTemplateExtractorFn = __nopPromptTemplateExtractor

###

def _header_offset_prompt_template_extractor(headingLevel: int, headingRegex: str, offset: int, modelInfo: ModelInfo, modelCard: ModelCard, __:BaseConfigData) -> Optional[AutomaticPromptTemplateResult]:
    ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
    if ast != None and ast['children'] != None:
        for i in range(len(ast['children'])):
            c = ast['children'][i]
            if c['type'] == 'Heading' and c['level'] == headingLevel:
                c2 = c['children'][0]
                if c2['type'] == 'RawText':
                    rm = regex.match(headingRegex, c2['content'])
                    if rm is not None:
                        promptTitle = rm.group(1)
                        if len(promptTitle) > 0:
                            return AutomaticPromptTemplateResult(modelInfo, promptTitle, ast['children'][i + offset]['children'][0]['content'])
    return None            

def build_header_offset_prompt_template_extractor(headingLevel: int, headingRegex: str, offset: int) -> PromptTemplateExtractorFn:
    return partial(_header_offset_prompt_template_extractor, headingLevel, headingRegex, offset)

###

# NOTE: fixedTitle last, experimentally partial the partial for name binding?
def _header_regex_prompt_template_extractor(tokenType: str, childDistance: int, substitutionTests: Dict[str,str], fixedTitle: str, modelInfo: ModelInfo, modelCard: ModelCard, __:BaseConfigData) -> Optional[AutomaticPromptTemplateResult]:
    ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
    if ast != None and ast['children'] != None:
        for i in range(len(ast['children'])):
            c = ast['children'][i]
            if c["type"] == tokenType:
                c2content = c["children"][childDistance]['content']
                for k in substitutionTests.keys():
                    m = regex.match(k, c2content)
                    if m != None:
                        return AutomaticPromptTemplateResult(modelInfo, fixedTitle, c2content)

    return None

def build_header_regex_prompt_template_extractor(tokenType: str, childDistance: int, substitutionTests: Dict[str,str], fixedTitle: str) -> PromptTemplateExtractorFn:
    return partial(_header_regex_prompt_template_extractor, tokenType, childDistance, substitutionTests, fixedTitle)

###

def _fixed_title_top_level_type_prompt_template_extractor(fixedTitle: str, tokenType: str, matchOffset: int, modelInfo: ModelInfo, modelCard: ModelCard, __:BaseConfigData) -> Optional[AutomaticPromptTemplateResult]:
    ast = ast_renderer.get_ast(Document(modelCard.text.split('\n')))
    if ast != None and ast['children'] != None:
        # weirdly manual loop is because some versions of this code cared about absolute indexes, and I'm still not sure that combining both of these together isn't the right idea
        # change this in v2 if this does not come back :D
        countOffset = 0
        for i in range(len(ast['children'])):
            c = ast['children'][i]
            if c["type"] == tokenType:
                if matchOffset == countOffset:
                    return AutomaticPromptTemplateResult(modelInfo, fixedTitle, c["children"][0]['content'])
                countOffset = countOffset + 1

    return None

def build_fixed_title_top_level_type_prompt_template_extractor(fixedTitle: str, tokenType: str, matchOffset: int) -> PromptTemplateExtractorFn:
    return partial(_fixed_title_top_level_type_prompt_template_extractor, fixedTitle, tokenType, matchOffset)

###

def _split_prompt_template_extractor(nameRecognizer: PromptTemplateExtractorFn, bodyRecognizer: PromptTemplateExtractorFn, modelInfo: ModelInfo, modelCard: ModelCard, baseConfigData:BaseConfigData) -> Optional[AutomaticPromptTemplateResult]:
    nr = nameRecognizer(modelInfo, modelCard, baseConfigData)
    br = bodyRecognizer(modelInfo, modelCard, baseConfigData)
    if nr is None or br is None:
        return None
    return AutomaticPromptTemplateResult(
        modelInfo=modelInfo,
        templateName=nr.templateName,
        templateBody=br.templateBody,
    )

def build_split_prompt_template_extractor(nameRecognizer: PromptTemplateExtractorFn, bodyRecognizer: PromptTemplateExtractorFn) -> PromptTemplateExtractorFn:
    return partial(_split_prompt_template_extractor, nameRecognizer, bodyRecognizer)