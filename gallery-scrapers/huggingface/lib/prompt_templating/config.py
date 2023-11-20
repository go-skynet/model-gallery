from typing import Set, Optional

from lib.base_models import LocalAIEndpoints
from lib.filter import ModelInfoFilterFn, _neverModelInfoFilter
from .extractor import PromptTemplateExtractorFn, _nopPromptTemplateExtractor
from .adapter import PromptTemplateAdapterFn, _nopAdapterFn

class AutoPromptTemplateConfig:
    def __init__(self, id: str, filter: Optional[ModelInfoFilterFn], extractPrompt: Optional[PromptTemplateExtractorFn], adaptPrompt: Optional[PromptTemplateAdapterFn], permittedEndpoints: Optional[Set[LocalAIEndpoints]]):
        self.id = id
        self.filter = filter or _neverModelInfoFilter
        self.extractPrompt = extractPrompt or _nopPromptTemplateExtractor
        self.adaptPrompt = adaptPrompt or _nopAdapterFn
        self.permittedEndpoints= permittedEndpoints or set()    # If this isn't overriden, fail to replace anything for safety.
