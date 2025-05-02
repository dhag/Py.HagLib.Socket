from enum import IntEnum
from typing import Dict, Optional
import asyncio
from .packet_callbacks import IPacketCallbacks, PacketCallbacksBase
from .packet_frame import PacketFrame


class SocketType(IntEnum):
    """ソケットタイプを定義するEnum"""
    Pipe = 0
    Tcp = 1
    Udp = 2


class IClientSession:
    """クライアントセッションインターフェース"""
    
    @property
    def group_id(self) -> int:
        """グループID"""
        return 0
        
    @group_id.setter
    def group_id(self, value: int) -> None:
        pass
        
    @property
    def user_id(self) -> int:
        """ユーザーID"""
        return 0
        
    @user_id.setter
    def user_id(self, value: int) -> None:
        pass
        
    @property
    def name(self) -> Optional[str]:
        """セッション名"""
        return None
        
    @name.setter
    def name(self, value: Optional[str]) -> None:
        pass
        
    @property
    def is_alive(self) -> bool:
        """セッションが生きているかどうか"""
        return False


class IServer(IPacketCallbacks):
    """サーバーインターフェース"""
    
    @property
    def name(self) -> str:
        """サーバー名"""
        return ""
        
    @name.setter
    def name(self, value: str) -> None:
        pass
        
    @property
    def sessions(self) -> Dict[int, IClientSession]:
        """セッション一覧"""
        return {}
        
    async def start_async(self, port_number: int) -> None:
        """サーバーを開始する"""
        pass
        
    async def send_data_async(self, packet_data: PacketFrame) -> None:
        """データを送信する"""
        pass
        
    def stop(self) -> None:
        """サーバーを停止する"""
        pass


class ServerBase(PacketCallbacksBase, IServer):
    """サーバー基底クラス"""
    
    def __init__(self):
        super().__init__()
        self._name = ""
        
    @property
    def name(self) -> str:
        return self._name
        
    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        
    @property
    def sessions(self) -> Dict[int, IClientSession]:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement sessions property")
        
    async def start_async(self, port_number: int) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement start_async method")
        
    async def send_data_async(self, packet_data: PacketFrame) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement send_data_async method")
        
    def stop(self) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement stop method")


class IClient(IPacketCallbacks):
    """クライアントインターフェース"""
    
    @property
    def name(self) -> str:
        """クライアント名"""
        return ""
        
    @name.setter
    def name(self, value: str) -> None:
        pass
        
    @property
    def user_id(self) -> int:
        """ユーザーID"""
        return 0
        
    @property
    def group_id(self) -> int:
        """グループID"""
        return 0
        
    @group_id.setter
    def group_id(self, value: int) -> None:
        pass
        
    @property
    def is_alive(self) -> bool:
        """クライアントが生きているかどうか"""
        return False
        
    async def connect_async(self, server_name: str, port_number: int, client_user_id: int, client_group_id: int) -> None:
        """サーバーに接続する"""
        pass
        
    async def send_data_async(self, packet_data: PacketFrame) -> None:
        """データを送信する"""
        pass
        
    def disconnect(self) -> None:
        """切断する"""
        pass
        
    def dispose(self) -> None:
        """リソースを解放する"""
        pass


class ClientBase(PacketCallbacksBase, IClient):
    """クライアント基底クラス"""
    
    def __init__(self):
        super().__init__()
        self._name = ""
        self._user_id = 0
        self._group_id = 0
        
    @property
    def name(self) -> str:
        return self._name
        
    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        
    @property
    def user_id(self) -> int:
        return self._user_id
        
    @property
    def group_id(self) -> int:
        return self._group_id
        
    @group_id.setter
    def group_id(self, value: int) -> None:
        self._group_id = value
        
    @property
    def is_alive(self) -> bool:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement is_alive property")
        
    async def connect_async(self, server_name: str, port_number: int, client_user_id: int, client_group_id: int) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement connect_async method")
        
    async def send_data_async(self, packet_data: PacketFrame) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement send_data_async method")
        
    def disconnect(self) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement disconnect method")
        
    def dispose(self) -> None:
        """実装クラスでオーバーライドする必要がある"""
        raise NotImplementedError("Derived classes must implement dispose method")