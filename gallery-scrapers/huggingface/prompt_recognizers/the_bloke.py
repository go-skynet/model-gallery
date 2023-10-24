from functools import partial

from lib.base_models import LocalAIEndpoints

from lib.prompt_templating import PromptTemplateRecognizer, header_offset_prompt_recognizer, adapt_prompt_template_simple_defaults_replacements
from lib.config_recognizer import model_author_filter, alwaysModelInfoFilter


__the_bloke_recognize_function = partial(header_offset_prompt_recognizer, 2, r'(?i)prompt template:\s+(.+)', 1)


the_bloke_strict = PromptTemplateRecognizer(id="TheBlokeStrict", 
    filter=partial(model_author_filter, "TheBloke"),
    recognizePrompt=__the_bloke_recognize_function,
    adaptPrompt=adapt_prompt_template_simple_defaults_replacements,
    permittedEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
)

the_bloke_style = PromptTemplateRecognizer(id="TheBlokeStyle", 
    filter=alwaysModelInfoFilter,
    recognizePrompt=__the_bloke_recognize_function,
    adaptPrompt=adapt_prompt_template_simple_defaults_replacements,
    permittedEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
)