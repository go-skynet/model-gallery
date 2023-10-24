from typing import Optional
from huggingface_hub.hf_api import ModelInfo, RepoFile
from deepmerge import conservative_merger
from functools import partial

from lib.base_models import BaseConfigData
from lib.config_recognizer import ConfigRecognizer, model_multi_author_filter, fixed_BaseConfigData_handler


def determine_bert_backend_version(repoFile: RepoFile) -> Optional[str]:
    # huggingface models
    if repoFile.rfilename.find("ggml") != -1:
        return "bert-embeddings"
    # sentence-transformer usually downloads its own models, right? handle that later.
    return None

def bert_recognizer_repo_file(_: ModelInfo, repoFile: RepoFile, baseConfig: BaseConfigData) -> BaseConfigData:
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
    filter=partial(model_multi_author_filter, {"skeskinen", "gruber"}),
    perRepo=partial(fixed_BaseConfigData_handler, data=BaseConfigData(
        config_file= {
            "embeddings": True
        },
    )), 
    perFile=bert_recognizer_repo_file, 
    autoPromptEndpoints=None
)
