from huggingface_hub.hf_api import ModelInfo
from huggingface_hub import ModelCard
from typing import Optional


from lib.base_models import LocalAIEndpoints, BaseConfigData
from lib.prompt_templating import AutoPromptTemplateConfig, AutomaticPromptTemplateResult, AutomaticPromptTemplateResultBundle, PromptTemplateExtractorFn, PromptTemplateAdapterFn, adapt_prompt_template_extract_roles_simple, build_adapt_prompt_template_regex_replace_variable_names, build_header_regex_prompt_template_extractor

from config_recognizers.rwkv import rwkv_model_info_filter

rwkv_prompt_regex_map =  {
    r': x{5,}': r": {{.Input}}"
}

rwkv_regex_extractor: PromptTemplateExtractorFn = build_header_regex_prompt_template_extractor('CodeFence', 0, rwkv_prompt_regex_map, 'rwkv-regex')

rwkv_variable_name_replacer: PromptTemplateAdapterFn = build_adapt_prompt_template_regex_replace_variable_names(rwkv_prompt_regex_map)

def rwkv_adapter(promptTemplateResult: AutomaticPromptTemplateResult, card: ModelCard, baseConfigData: BaseConfigData) -> Optional[AutomaticPromptTemplateResultBundle]:
    # TODO: More elegant way to pipeline this?
    bundle = rwkv_variable_name_replacer(promptTemplateResult, card, baseConfigData)
    
    if bundle is None:
        return None
    
    bundle = adapt_prompt_template_extract_roles_simple(bundle.result, card, bundle.config)

    return bundle

rwkv_by_tag = AutoPromptTemplateConfig(id="rwkv-by-tag-and-prompt-regex", 
    filter=rwkv_model_info_filter,
    extractPrompt=rwkv_regex_extractor,
    adaptPrompt=rwkv_adapter,
    permittedEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
)
