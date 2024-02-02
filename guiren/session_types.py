from enum import Enum
from uuid import UUID, uuid4
import typing as t
from pydantic import BaseModel, model_validator, Field

__all__ = [
    "SessionType",
    "SessionConnectionInfo",
    "SessionInfo",
    "SessionConnOnelinePHP",
    "type_to_class",
]


class SessionType(Enum):
    """session的类型"""

    ONELINE_PHP = "ONELINE_PHP"
    BEHINDER_PHP_AES = "BEHINDER_PHP_AES"


# 各个session的连接信息
class SessionConnectionInfoBase(BaseModel):
    """session的连接信息"""


class SessionConnOnelinePHP(SessionConnectionInfoBase):
    """PHP一句话webshell的连接信息"""

    url: str
    password: str
    method: str
    http_params_obfs: bool
    encoder: t.Literal["raw", "base64"] = "raw"


class SessionConnBehinderPHPAES(SessionConnectionInfoBase):
    """PHP一句话webshell的连接信息"""

    url: str
    password: str
    encoder: t.Literal["raw", "base64"] = "raw"


SessionConnectionInfo = t.Union[SessionConnOnelinePHP, SessionConnBehinderPHPAES]


class SessionInfo(BaseModel):
    """session的基本信息"""

    session_type: SessionType
    name: str
    connection: SessionConnectionInfo
    session_id: UUID = Field(default_factory=uuid4)
    note: str = ""
    location: str = ""

    @model_validator(mode="after")
    def validator(self):
        conn_class = type_to_class[self.session_type]
        if not isinstance(self.connection, conn_class):
            raise ValueError(f"Wrong connection data for {self.session_type}")
        return self

    class Config:
        from_attributes = True


type_to_class = {
    SessionType.ONELINE_PHP: SessionConnOnelinePHP,
    SessionType.BEHINDER_PHP_AES: SessionConnBehinderPHPAES,
}

