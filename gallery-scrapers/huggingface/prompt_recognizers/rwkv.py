from functools import partial
from huggingface_hub.hf_api import ModelInfo
from huggingface_hub import ModelCard
from typing import Optional


from lib.base_models import LocalAIEndpoints, BaseConfigData
from lib.prompt_templating import PromptTemplateRecognizer, PromptTemplateRecognizerResult, adapt_prompt_template_extract_roles_simple, fixed_title_top_level_type_prompt_recognizer, adapt_prompt_template_regex_replace_variable_names, header_regex_prompt_recognizer
from lib.config_recognizer import ModelInfoFilterFunctionType

from config_recognizers.rwkv import rwkv_model_info_filter

rwkv_prompt_regex_map =  {
    r': x{5,}': r": {{.Input}}"
}

# partial(fixed_title_top_level_type_prompt_recognizer, 'rwkv', 'CodeFence', 0),

rwkv_regex_recognizer = partial(header_regex_prompt_recognizer, 'CodeFence', 0, rwkv_prompt_regex_map, 'rwkv-regex')

rwkv_variable_name_replacer = partial(adapt_prompt_template_regex_replace_variable_names, rwkv_prompt_regex_map)

def rwkv_adapter(promptTemplateResult: PromptTemplateRecognizerResult, modelInfo: ModelInfo, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[PromptTemplateRecognizerResult]:
    (promptTemplateResult, baseConfigData) = rwkv_variable_name_replacer(promptTemplateResult, modelInfo, card, baseConfigData)
    (promptTemplateResult, baseConfigData) = adapt_prompt_template_extract_roles_simple(promptTemplateResult, modelInfo, card, baseConfigData)

    return (promptTemplateResult, baseConfigData)

rwkv_by_tag = PromptTemplateRecognizer(id="rwkv-by-tag-and-prompt-regex", 
    filter=rwkv_model_info_filter,
    recognizePrompt=rwkv_regex_recognizer,
    adaptPrompt=rwkv_adapter,
    permittedEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
)
