from typing import Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile
from deepmerge import conservative_merger

from lib.base_models import BaseConfigData
from lib.config_recognizer import ConfigRecognizer, build_fixed_BaseConfigData_handler
from lib.filter import build_multi_author_model_info_filter


def determine_bert_backend_version(repoFile: RepoFile) -> Optional[str]:
    # huggingface models
    if repoFile.rfilename.find("ggml") != -1:
        return "bert-embeddings"
    # sentence-transformer usually downloads its own models, right? handle that later.
    return None

def bert_recognizer_repo_file(_: ModelInfo, repoFile: RepoFile, baseConfig: BaseConfigData) -> Optional[BaseConfigData]:
    backend = determine_bert_backend_version(repoFile)
    
    if backend == None:
        return None
    
    baseConfig.config_file = conservative_merger.merge(baseConfig.config_file, {
        "backend": backend
    })

    return baseConfig

bertCppConfigRecognizer = ConfigRecognizer(
    id="bert.cpp",
    # bert.cpp model cards on HF seem to be... quite lacking in recognizable features.
    # therefore, this will serve as a demo for a simpler way to configure a ConfigRecognizer:
    filter=build_multi_author_model_info_filter({"skeskinen", "gruber"}),
    perRepo=build_fixed_BaseConfigData_handler(BaseConfigData(
        config_file= {
            "embeddings": True
        },
    )), 
    perFile=bert_recognizer_repo_file, 
    autoPromptEndpoints=None
)
