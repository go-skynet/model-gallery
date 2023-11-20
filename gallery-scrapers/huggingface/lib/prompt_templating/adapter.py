from functools import partial
from typing import Callable, Dict, List, Optional
from huggingface_hub import ModelCard
from huggingface_hub.hf_api import ModelInfo

import regex

from lib.base_models import BaseConfigData

from .result import AutomaticPromptTemplateResult, AutomaticPromptTemplateResultBundle

PromptTemplateAdapterFn = Callable[[AutomaticPromptTemplateResult, ModelCard, BaseConfigData], Optional[AutomaticPromptTemplateResultBundle]]

###

def __nopAdapterFn(result: AutomaticPromptTemplateResult, _: ModelCard, config: BaseConfigData) -> Optional[AutomaticPromptTemplateResultBundle]:
    return AutomaticPromptTemplateResultBundle(result, config)

_nopAdapterFn: PromptTemplateAdapterFn = __nopAdapterFn

###

def _adapt_prompt_template_simple_replace_variable_names(substitutions: Dict[str,str], promptTemplateResult: AutomaticPromptTemplateResult, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[AutomaticPromptTemplateResultBundle]:
    for k, v in substitutions.items():
        promptTemplateResult.templateBody = promptTemplateResult.templateBody.replace(k, v)

    return AutomaticPromptTemplateResultBundle(promptTemplateResult, baseConfigData)

def build_adapt_prompt_template_simple_replace_variable_names(substitutions: Dict[str,str]) -> PromptTemplateAdapterFn:
    return partial(_adapt_prompt_template_simple_replace_variable_names, substitutions)

_adapt_prompt_template_variable_names_default_substitutions = {
    r"{prompt}": r"{{.Input}}",
    r"{system}": r"{{.SystemPrompt}}",
    r"{system_message}": r"{{.SystemPrompt}}",
    # todo: is this next one a good idea?
    r"{input}": r"{{.Input}}"
}

adapt_prompt_template_simple_defaults_replacements = build_adapt_prompt_template_simple_replace_variable_names(_adapt_prompt_template_variable_names_default_substitutions)

###

def _adapt_prompt_template_regex_replace_variable_names(substitutions: Dict[str,str], promptTemplateResult: AutomaticPromptTemplateResult, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[AutomaticPromptTemplateResultBundle]:
    for k, v in substitutions.items():
        promptTemplateResult.templateBody = regex.sub(k, v, promptTemplateResult.templateBody)

    return AutomaticPromptTemplateResultBundle(promptTemplateResult, baseConfigData)

def build_adapt_prompt_template_regex_replace_variable_names(substitutions: Dict[str,str]) -> PromptTemplateAdapterFn: 
    return partial(_adapt_prompt_template_regex_replace_variable_names, substitutions)

###

def _adapt_prompt_template_replace_extracted_with_fixed_value(promptTemplateResult: AutomaticPromptTemplateResult, _ignored: AutomaticPromptTemplateResult, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[AutomaticPromptTemplateResultBundle]:
    return AutomaticPromptTemplateResultBundle(promptTemplateResult, baseConfigData)

def build_adapt_prompt_template_replace_extracted_with_fixed_value(promptTemplateResult: AutomaticPromptTemplateResult) -> PromptTemplateAdapterFn:
    return partial(_adapt_prompt_template_replace_extracted_with_fixed_value, promptTemplateResult)

###

# Not totally sure this is the right place to be doing this... but for v1 it'll work.
def _adapt_prompt_template_extract_roles(roleRegex: str, promptTemplateResult: AutomaticPromptTemplateResult, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[AutomaticPromptTemplateResultBundle]:

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

    return AutomaticPromptTemplateResultBundle(promptTemplateResult, baseConfigData)

def build_adapt_prompt_template_extract_roles(roleRegex: str) -> PromptTemplateAdapterFn:
    return partial(_adapt_prompt_template_extract_roles, roleRegex)

adapt_prompt_template_extract_roles_simple = build_adapt_prompt_template_extract_roles(r"(.*):")
