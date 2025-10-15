from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from requests.cookies import RequestsCookieJar


@dataclass
class MetaData:
    name: Optional[str] = None
    value: Optional[str] = None
    meta_type: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'MetaData':
        return cls(**data)


@dataclass
class File:
    id: Optional[str] = None
    name: Optional[str] = None
    deposit_date: Optional[str] = None
    extension: Optional[str] = None
    user_id: Optional[str] = None
    folder_id: Optional[str] = None
    is_favorite: bool = False
    is_new: bool = False
    is_perso: bool = False
    type_code: Optional[str] = None
    issuer_name: Optional[str] = None
    meta_datas: List[MetaData] = field(default_factory=list)
    type: Optional[str] = None
    is_visible: bool = False
    sharing_duplication: bool = False
    file_size: int = 0
    dispatch_id: Optional[str] = None
    dispatched_doc_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'File':
        meta_datas = []
        for meta_data in data.get('meta_datas', []):
            meta_datas.append(MetaData(**meta_data))
        data['meta_datas'] = meta_datas
        return cls(**data)


@dataclass
class Folder:
    name: Optional[str] = None
    type: Optional[str] = None
    folder_id: Optional[str] = None
    code: Optional[str] = None
    children: List[Union[File, 'Folder']] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> Union[File, 'Folder']:
        children = []
        for child in data.get('children', []):
            if child.get('type') == 'folder':
                children.append(Folder.from_dict(child))
            elif child.get('type') == 'file':
                children.append(File.from_dict(child))
        data['children'] = children
        return cls(**data)


@dataclass
class Response:
    status: Optional[str] = None
    code: int = 0
    content: List[Folder] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Response':
        content = []
        for item in data.get('content', []):
            content.append(Folder.from_dict(item))
        data['content'] = content
        return cls(**data)

@dataclass
class Context:
    token: Optional[str] = None
    cookies: Optional[RequestsCookieJar] = None
