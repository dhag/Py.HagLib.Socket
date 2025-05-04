#Py.HagLib.Socket/Socket/tcp_client.py
import asyncio
import socket
from typing import Optional
from .socket_interfaces import ClientBase
from .packet_callbacks import PacketProcessor
from .packet_frame import PacketFrame, debug_print
from .tcp_protocol import TcpProtocol


class TcpClient(ClientBase):
    """TCP通信を行うクライアントクラス"""
    
    def __init__(self):
        super().__init__()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._processor = PacketProcessor(self)
        self._connected = False
        self._session_id = 0  # サーバーから割り当てられるセッションID
        
    @property
    def is_alive(self) -> bool:
        return self._connected and self._writer is not None and not self._writer.is_closing()
    
    @property
    def session_id(self) -> int:
        return self._session_id
        
    async def connect_async(self, server_name: str, port_number: int, client_user_id: int, client_group_id: int) -> None:
        """
        サーバーに接続する
        
        Args:
            server_name: サーバーのホスト名またはIPアドレス
            port_number: サーバーのポート番号（C#版では pipe_name だが、TCPでは port_number）
            client_user_id: クライアントのユーザーID
            client_group_id: クライアントのグループID
        """
        if self.is_alive:
            return
            
        try:
            # サーバーに接続
            self._reader, self._writer = await asyncio.open_connection(server_name, port_number)
            
            # クライアント情報を設定
            self._user_id = client_user_id
            self._group_id = client_group_id
            self._connected = True
            
            # 接続完了後の待機（安定化のため）
            await asyncio.sleep(0.5)
            
            # 初期ハンドシェイクパケットの送信（サーバーに自分の情報を伝える）
            handshake_packet = PacketFrame.from_text(
                f"CONNECT:{client_user_id}:{client_group_id}",
                destination_user_id=0,  # サーバー宛て
                source_user_id=client_user_id,
                source_group_id=client_group_id
            )
            await self._send_raw_packet(handshake_packet)
            
            # 受信タスクを開始
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            self.raise_log_message(f"サーバー {server_name}:{port_number} に接続しました")
            
        except Exception as e:
            self.raise_log_message(f"接続中にエラーが発生しました: {e}")
            self.disconnect()
            
    async def _receive_loop(self) -> None:
        """サーバーからデータを受信し続けるループ"""
        try:
            while self.is_alive and self._reader is not None:
                # 完全なパケットを待機
                packet = await TcpProtocol.receive_packet(self._reader)
                if packet is None:
                    debug_print("パケットの読み込みに失敗しました")
                    break
                
                # セッションIDはクライアント側では特に処理不要
                if packet.payload_type == 1:  # PlainText
                    message = packet.payload.decode('utf-8', errors='ignore')
                    if message.startswith("ようこそ！"):
                        debug_print("サーバーからウェルカムメッセージを受信しました")
                
                # パケットを処理
                self._processor.process_packet(packet, "Server")
                    
        except asyncio.CancelledError:
            # タスクがキャンセルされた
            debug_print("受信タスクがキャンセルされました")
            pass
        except ConnectionResetError:
            # 接続がリセットされた
            debug_print("接続がリセットされました")
            pass
        except Exception as e:
            self.raise_log_message(f"受信ループでエラーが発生: {e}")
        finally:
            self.disconnect()
    
    async def _send_raw_packet(self, packet: PacketFrame) -> None:
        """
        生のパケットデータを送信する（内部メソッド）
        """
        if not self.is_alive or self._writer is None:
            raise ConnectionError("サーバーに接続されていません")
            
        try:
            await TcpProtocol.send_packet(self._writer, packet)
        except Exception as e:
            self.raise_log_message(f"データ送信中にエラーが発生: {e}")
            raise
    
    async def send_data_async(self, packet_data: PacketFrame) -> None:
        """
        サーバーにデータを送信する
        
        Args:
            packet_data: 送信するパケット
        """
        if not self.is_alive or self._writer is None:
            raise ConnectionError("サーバーに接続されていません")
            
        try:
            # 送信元情報を設定（すでに設定されている場合は上書きしない）
            if packet_data.source_group_id == 0:
                packet_data.source_group_id = self.group_id
            if packet_data.source_user_id == 0xFFFF:
                packet_data.source_user_id = self.user_id
            
            await self._send_raw_packet(packet_data)
            
        except Exception as e:
            self.raise_log_message(f"データ送信中にエラーが発生: {e}")
            self.disconnect()
            raise
            
    def disconnect(self) -> None:
        """サーバーから切断する"""
        self._connected = False
        
        # 受信タスクをキャンセル
        if self._receive_task is not None and not self._receive_task.done():
            self._receive_task.cancel()
            
        # 接続を閉じる
        if self._writer is not None and not self._writer.is_closing():
            self._writer.close()
            
        self.raise_log_message("サーバーから切断しました")
            
    def dispose(self) -> None:
        """リソースを解放する"""
        self.disconnect()