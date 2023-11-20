from functools import partial

from lib.base_models import LocalAIEndpoints
from lib.prompt_templating import AutoPromptTemplateConfig, build_header_offset_prompt_template_extractor, adapt_prompt_template_simple_defaults_replacements
from lib.filter import build_author_model_info_filter, _alwaysModelInfoFilter


__the_bloke_extractor_function = build_header_offset_prompt_template_extractor(2, r'(?i)prompt template:\s+(.+)', 1)


the_bloke_strict = AutoPromptTemplateConfig(id="TheBlokeStrict", 
    filter=build_author_model_info_filter("TheBloke"),
    extractPrompt=__the_bloke_extractor_function,
    adaptPrompt=adapt_prompt_template_simple_defaults_replacements,
    permittedEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
)

the_bloke_style = AutoPromptTemplateConfig(id="TheBlokeStyle", 
    filter=_alwaysModelInfoFilter,
    extractPrompt=__the_bloke_extractor_function,
    adaptPrompt=adapt_prompt_template_simple_defaults_replacements,
    permittedEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
)