from typing import Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile
from deepmerge import conservative_merger

from lib.base_models import BaseConfigData, LocalAIEndpoints
from lib.config_recognizer import ConfigRecognizer, build_fixed_BaseConfigData_handler
from lib.filter import build_tag_based_model_info_filter


def determine_llama_backend_version(repoFile: RepoFile) -> Optional[str]:
    if repoFile.rfilename.endswith(".gguf"):
        return "llama"
    elif repoFile.rfilename.find("ggml") != -1:
        return "llama-stable"
    return None


def llama_recognizer_repo_file(_: ModelInfo, repoFile: RepoFile, baseConfig: BaseConfigData) -> Optional[BaseConfigData]:
    backend = determine_llama_backend_version(repoFile)
    
    if backend == None:
        return None
    
    baseConfig.config_file = conservative_merger.merge(baseConfig.config_file, {
        "backend": backend
    })

    return baseConfig

   
llamaConfigRecognizer = ConfigRecognizer(
    id="llama", 
    filter=build_tag_based_model_info_filter({"llama", "llama-2"}, '(?i)llama'),
    perRepo=build_fixed_BaseConfigData_handler(BaseConfigData(
        config_file= {
            "context_size": 1024
        },
    )), 
    perFile=llama_recognizer_repo_file, 
    autoPromptEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION}
)


llama2ChatConfigRecognizer = ConfigRecognizer(
    id="llama2Chat", 
    filter=build_tag_based_model_info_filter({"llama2-chat"}, '(?i)llama2-chat'),
    perRepo=build_fixed_BaseConfigData_handler(BaseConfigData(
       config_file= {
            "context_size": 4096
        },
    )),
    perFile=llama_recognizer_repo_file,
    autoPromptEndpoints={LocalAIEndpoints.CHAT}
)

mistralConfigRecognizer = ConfigRecognizer(
    id="mistral",
    filter=build_tag_based_model_info_filter({"mistral"}, '(?i)mistral'),
    perRepo=build_fixed_BaseConfigData_handler(BaseConfigData(
        config_file= {
            "context_size": 4096,
            "f16": True,
            "stopwords": ["<|im_end|>"],
            "mmap": True
        },
    )),
    perFile=llama_recognizer_repo_file, 
    autoPromptEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION}
)

llamaFallbackConfigRecognizer = ConfigRecognizer(
    id="llamaFallback",
    filter=build_tag_based_model_info_filter({"text-generation"}, '(?i)llama'),
    perRepo=build_fixed_BaseConfigData_handler(BaseConfigData(
        config_file= {
            "context_size": 1024
        },
    )), 
    perFile=llama_recognizer_repo_file, 
    autoPromptEndpoints={LocalAIEndpoints.CHAT, LocalAIEndpoints.COMPLETION},
    priority=0
)