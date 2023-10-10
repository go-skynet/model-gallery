from typing import Callable, List, Dict, Any, Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile

from lib.base_models import BaseConfigData

import regex

ModelInfoFilterFunctionType = Callable[[ModelInfo], bool]
PerRepoRecognizerFunctionType = Callable[[ModelInfo], BaseConfigData]
PerFileRecognizerFunctionType = Callable[[ModelInfo, RepoFile, BaseConfigData], Optional[BaseConfigData]]

# Pickling lambdas doesn't work, pickling closures doesn't work.
# However, we _can_ pickle functools.partial the arguments - recognizedTags and fallbackRegex must be captured.
def tag_based_filter_for_model(recognizedTags: List[str], fallbackRegex: str, modelInfo: ModelInfo) -> bool:
    if modelInfo == None:
        return False
    elif len(modelInfo.tags) > 0:
        return any(item in recognizedTags for item in modelInfo.tags)
    else:
        return regex.match(fallbackRegex, modelInfo.modelId) != None
    
def model_author_filter(author: str, model: ModelInfo) -> bool:
    return model.author == author

# these three "nop" functions exist to avoid issues with Pickle, which is used by the multiprocessing stuff.
# This is perhaps not the pythonic way to do this. Please help.

def neverModelInfoFilter(_):
    return False

def alwaysModelInfoFilter(_):
    return True

def nopConfigRecognizerPerRepoFn(_):
    return None

def nopConfigRecognizerPerFileFn(_, __, orig):
    return orig

# TODO: this really looks wrong and dumb. Can I remove without breaking pickle again?
# As far as I know, this silly *args that we ignore is the best way to closure a parameter with partial
def fixed_BaseConfigData_handler(*args, data: BaseConfigData):
    return data

class ConfigRecognizer:
    def __init__(self, id: str, filter: ModelInfoFilterFunctionType, perRepo: PerRepoRecognizerFunctionType, perFile: PerFileRecognizerFunctionType, autoPromptEndpoints: Optional[List[str]]):
        self.id = id
        self.filter = filter or neverModelInfoFilter # Must be overriden for your ConfigRecognizer to be useful.
        self.perRepo = perRepo or nopConfigRecognizerPerRepoFn # If perRepo action isn't set, return None. This can then be detected.
        self.perFile = perFile or nopConfigRecognizerPerFileFn # If perFile action isn't set, return the BaseConfigData parameter unmodified. This will be the result of perRepo, which may itself be None.
        self.autoPromptEndpoints = autoPromptEndpoints # If this is None, automatic prompt templating is skipped and the perRepo action must handle that. If it is set to a list of string, auto will put the selected prompt template in each listed endpoint for the generated config.
