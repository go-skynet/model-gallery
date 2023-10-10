from typing import Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile
from deepmerge import conservative_merger
from functools import partial

from lib.base_models import BaseConfigData
from lib.config_recognizer import ConfigRecognizer, tag_based_filter_for_model, fixed_BaseConfigData_handler


def determine_llama_backend_version(repoFile: RepoFile) -> Optional[str]:
    if repoFile.rfilename.endswith(".gguf"):
        return "llama"
    elif repoFile.rfilename.find("ggml") != -1:
        return "llama-stable"
    return None


def llama_recognizer_repo_file(_: ModelInfo, repoFile: RepoFile, baseConfig: BaseConfigData) -> BaseConfigData:
    backend = determine_llama_backend_version(repoFile)
    
    if backend == None:
        return None
    
    baseConfig.config_file = conservative_merger.merge(baseConfig.config_file, {
        "backend": backend
    })

    return baseConfig

   
llamaConfigRecognizer = ConfigRecognizer(
    id="llama", 
    filter=partial(tag_based_filter_for_model, ["llama", "llama-2"], '(?i)llama'),
    perRepo=partial(fixed_BaseConfigData_handler, data=BaseConfigData(
        config_file= {
            "context_size": 1024
        },
    )), 
    perFile=llama_recognizer_repo_file, 
    autoPromptEndpoints=["chat"]
)


llama2ChatConfigRecognizer = ConfigRecognizer(
    id="llama", 
    filter=partial(tag_based_filter_for_model, ["llama2-chat"], '(?i)llama2-chat'),
    perRepo=partial(fixed_BaseConfigData_handler, data=BaseConfigData(
       config_file= {
            "context_size": 4096
        },
    )),
    perFile=llama_recognizer_repo_file,
    autoPromptEndpoints=["chat"]
)
