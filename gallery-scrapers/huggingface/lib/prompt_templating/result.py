from huggingface_hub.hf_api import ModelInfo
from lib.base_models import BaseConfigData

class AutomaticPromptTemplateResult:
    def __init__(self, modelInfo: ModelInfo, templateName: str, templateBody: str):
        self.modelInfo = modelInfo
        self.templateName = templateName
        self.templateBody = templateBody


class AutomaticPromptTemplateResultBundle:
    def __init__(self, result: AutomaticPromptTemplateResult, config: BaseConfigData):
        self.result = result
        self.config = config