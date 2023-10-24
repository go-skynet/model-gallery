from typing import List, Dict, Any, Optional

from enum import StrEnum

class LocalAIEndpoints(StrEnum):
    CHAT = 'chat'
    COMPLETION = 'completion'

## Shared Models

class Gallery:
    def __init__(self, URL: str, Name: str):
        self.url = URL
        self.name = Name

class DownloadableFile:
    def __init__(self, Filename: str, SHA256: str, URI: str):
        self.filename = Filename
        self.sha256 = SHA256
        self.uri = URI

class GalleryModel:
    def __init__(
        self,
        # url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        license: Optional[str] = None,
        urls: Optional[List[str]] = None,
        icon: Optional[str] = None,
        tags: Optional[List[str]] = None,
        config_file: Optional[Dict[str, Any]] = None,
        # overrides: Optional[Dict[str, Any]] = None,
        files: Optional[List[DownloadableFile]] = None,
        # gallery: Optional[Gallery] = None,        # ????
        # installed: Optional[bool] = None,         # Only adds useless lines to yaml
    ):
        # self.url = url
        self.name = name
        self.description = description
        self.license = license
        self.urls = urls or []
        self.icon = icon
        self.tags = tags or []
        self.config_file = config_file or {}
        # self.overrides = overrides or {}
        self.files = files or []
        # self.gallery = gallery
        # self.installed = installed


## Scraper Specific Models

class BaseConfigData:
    def __init__(
            self,
            config_file: Optional[Dict[str, Any]] = None,
            files: Optional[List[DownloadableFile]] = None,
    ):
        self.config_file = config_file or {}
        self.files = files or []

class ScrapeResultStatus(StrEnum):
    SUCCESS = 'success'
    EMPTY = 'empty'
    UNCHANGED = 'unchanged'
    ERROR = 'error'

class ScrapeResult:
    def __init__(self, filename: str, gallery: List[GalleryModel], status: ScrapeResultStatus, message: str = ""):
        self.filename = filename
        self.gallery = gallery
        self.status = status
        self.message = message or ""




# Not in use currently, but was earlier and may come back?
# The jury is still out if its better to generate base files and overrides or full files
# Some earlier versions used both, but currently I'm not sure that automatically generated overrides make sense.
class OverrideUrlConfigData:
    def __init__(
            self,
            path: Optional[str] = None,
            overrides: Optional[Dict[str, Any]] = None,
            files: Optional[List[DownloadableFile]] = None,
    ):
        self.path = path
        self.overrides = overrides or {}
        self.files = files or []