from abc import ABC, abstractmethod
from typing import Optional, Dict

class TransportBase(ABC):
    @abstractmethod
    def request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, **kwargs):
        pass
