from pathlib import Path
from typing import Dict, Set, Optional
from multiprocessing import Lock
from urllib.parse import urljoin

import hashlib
from traceback import print_exc

from lib.base_models import DownloadableFile

from .result import AutomaticPromptTemplateResult

_promptTemplateCacheLock = Lock()

class PromptTemplateCache:
    def __init__(self, templateRoot: Path, downloadRoot: str, bannedPromptNames: Optional[Set[str]]):
        self.templateRoot = templateRoot
        self.downloadRoot = downloadRoot
        self.bannedPromptNames: Set[str] = bannedPromptNames or {"", "none", "custom"}
        self.downloadableFileCache: Dict[str, DownloadableFile] = {}

    def get_prompt_template_directory_path(self) -> Path:
        return self.templateRoot

    def write_prompt_template_to_file(self, outputPath: Path, template: str):
        with open(outputPath, 'x') as outputFile:
            outputFile.writelines(template)

    def get_prompt_path(self, promptTemplateResult: AutomaticPromptTemplateResult) -> Optional[Path]:
        if promptTemplateResult.templateName.lower() in self.bannedPromptNames:
            promptTemplateResult.templateName = promptTemplateResult.modelInfo.modelId.replace("/", "__")
        promptTemplatePath = self.templateRoot / f"{promptTemplateResult.templateName}.tmpl"      
        if promptTemplatePath.exists():
            # TODO: Consider checking how different it is from the text match, since we already have the text body?
            # For now, always trust that the file is better than the regex, since it might be hand-edited.
            # print(f'Existing prompt template path {promptTemplatePath} already exists!')
            return promptTemplatePath
        try:
            self.write_prompt_template_to_file(promptTemplatePath, promptTemplateResult.templateBody)
            return promptTemplatePath
        except:
            return None
        
    def get_downloadable_file(self, promptTemplateResult: AutomaticPromptTemplateResult) -> Optional[DownloadableFile]:
        
        if promptTemplateResult.templateName in self.downloadableFileCache:
            # print(f"prompt template found in cache: {promptTemplateResult.templateName}")
            return self.downloadableFileCache[promptTemplateResult.templateName]
        
        # print(f"automatic prompt template caching started for {promptTemplateResult.templateName}")

        _promptTemplateCacheLock.acquire()
        try:
            pp = self.get_prompt_path(promptTemplateResult)
            if pp is None:
                _promptTemplateCacheLock.release()
                return None
            
            sha256: Optional[str] = None
            with open(pp, "rb") as f:
                sha256 = hashlib.file_digest(f, "sha256").hexdigest()

            df = DownloadableFile(
                Filename=f"{promptTemplateResult.templateName}.tmpl",
                SHA256=sha256,
                URI=urljoin(self.downloadRoot, f"{promptTemplateResult.templateName}.tmpl")
            )
            self.downloadableFileCache[promptTemplateResult.templateName] = df
            _promptTemplateCacheLock.release()
            return df
        except Exception as e:
            print(f"PromptTemplateCache::get_downloadable_file MAJOR ERROR: {e}\n{promptTemplateResult.modelInfo}\nTEMPLATE NAME:{promptTemplateResult.templateName}\nTEMPLATE BODY{promptTemplateResult.templateBody}\n\n")
            print_exc()
            _promptTemplateCacheLock.release()
            return None
    