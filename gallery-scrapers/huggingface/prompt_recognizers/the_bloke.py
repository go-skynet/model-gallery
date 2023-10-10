from functools import partial

from lib.prompt_templating import PromptTemplateRecognizer, header_offset_prompt_recognizer, adapt_prompt_template_variable_names
from lib.config_recognizer import model_author_filter, alwaysModelInfoFilter

the_bloke_strict = PromptTemplateRecognizer(id="TheBlokeStrict", 
    filter=partial(model_author_filter, "TheBloke"),
    recognizePrompt=partial(header_offset_prompt_recognizer, 2, r'(?i)prompt template:\s+(.+)', 1),
    adaptPrompt=adapt_prompt_template_variable_names,
)

the_bloke_style = PromptTemplateRecognizer(id="TheBlokeStyle", 
    filter=alwaysModelInfoFilter,
    recognizePrompt=partial(header_offset_prompt_recognizer, 2, r'(?i)prompt template:\s+(.+)', 1),
    adaptPrompt=adapt_prompt_template_variable_names,
)