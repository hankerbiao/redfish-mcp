from abc import ABC

class ResourceBase(ABC):
    def __init__(self, client):
        self._client = client
