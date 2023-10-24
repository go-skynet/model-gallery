
from typing import Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile
from deepmerge import conservative_merger
from functools import partial

from lib.base_models import BaseConfigData, LocalAIEndpoints
from lib.config_recognizer import ConfigRecognizer, tag_based_filter_for_model, fixed_BaseConfigData_handler


rwkv_model_info_filter = partial(tag_based_filter_for_model, {"rwkv"}, '(?i)rwkv')

def rwkv_recognizer_repo_file(_: ModelInfo, repoFile: RepoFile, baseConfig: BaseConfigData) -> BaseConfigData:
    if not repoFile.rfilename.endswith('.bin'):
        return None

    return baseConfig

   
rwkvConfigRecognizer = ConfigRecognizer(
    id="rwkv", 
    filter=rwkv_model_info_filter,
    perRepo=partial(fixed_BaseConfigData_handler, data=BaseConfigData(
        config_file= {
            "backend": "rwkv",
            "context_size": 1024
        },
    )),
    perFile=rwkv_recognizer_repo_file, 
    autoPromptEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION}
)

