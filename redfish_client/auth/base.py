
from abc import ABC, abstractmethod

class AuthBase(ABC):
    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def logout(self):
        pass

    @property
    @abstractmethod
    def default_restcall_header(self):
        pass
