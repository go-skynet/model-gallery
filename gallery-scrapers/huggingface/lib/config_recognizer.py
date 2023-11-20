from typing import Callable, Set, Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile
from functools import partial

from lib.base_models import BaseConfigData, LocalAIEndpoints
from lib.filter import ModelInfoFilterFn, _neverModelInfoFilter

PerRepoRecognizerFunctionType = Callable[[ModelInfo], BaseConfigData]
PerFileRecognizerFunctionType = Callable[[ModelInfo, RepoFile, BaseConfigData], Optional[BaseConfigData]]

def nopConfigRecognizerPerRepoFn(_):
    return None

def nopConfigRecognizerPerFileFn(_, __, orig):
    return orig

# TODO: once upon a time, this weird kargs method was the only way I knew how to do this. I've since cleaned this up elsewhere -
# This one has currently been granted a reprieve as it may be useful to have a fixed <ignore all args> -> BCD for now
def __fixed_BaseConfigData_handler(*args, data: BaseConfigData):
    return data

def build_fixed_BaseConfigData_handler(data: BaseConfigData):
    return partial(__fixed_BaseConfigData_handler, data=data)

class ConfigRecognizer:
    def __init__(self, id: str, filter: Optional[ModelInfoFilterFn], perRepo: Optional[PerRepoRecognizerFunctionType], perFile: Optional[PerFileRecognizerFunctionType], autoPromptEndpoints: Optional[Set[LocalAIEndpoints]], priority: Optional[int] = 1):
        self.id = id
        self.filter = filter or _neverModelInfoFilter # Must be overriden for your ConfigRecognizer to be useful.
        self.perRepo = perRepo or nopConfigRecognizerPerRepoFn # If perRepo action isn't set, return None. This can then be detected.
        self.perFile = perFile or nopConfigRecognizerPerFileFn # If perFile action isn't set, return the BaseConfigData parameter unmodified. This will be the result of perRepo, which may itself be None.
        self.autoPromptEndpoints = autoPromptEndpoints # If this is None, automatic prompt templating is skipped and the perRepo action must handle that. If it is a set of strings, auto will put the selected prompt template in each listed endpoint for the generated config.
        self.priority = priority or 1 # After filtering, active ConfigRecognizers are sorted by priority - currently, only the highest rank is kept?
