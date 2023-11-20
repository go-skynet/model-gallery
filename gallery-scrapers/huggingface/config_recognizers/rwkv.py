
from typing import Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile

from lib.base_models import BaseConfigData, LocalAIEndpoints
from lib.config_recognizer import ConfigRecognizer, build_fixed_BaseConfigData_handler
from lib.filter import build_tag_based_model_info_filter


rwkv_model_info_filter = build_tag_based_model_info_filter({"rwkv"}, '(?i)rwkv')

def rwkv_recognizer_repo_file(_: ModelInfo, repoFile: RepoFile, baseConfig: BaseConfigData) -> Optional[BaseConfigData]:
    if not repoFile.rfilename.endswith('.bin'):
        return None

    return baseConfig

   
rwkvConfigRecognizer = ConfigRecognizer(
    id="rwkv", 
    filter=rwkv_model_info_filter,
    perRepo=build_fixed_BaseConfigData_handler(BaseConfigData(
        config_file= {
            "backend": "rwkv",
            "context_size": 1024
        },
    )),
    perFile=rwkv_recognizer_repo_file, 
    autoPromptEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION}
)

