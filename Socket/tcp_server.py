#Py.HagLib.Socket/Socket/tcp_server.py
import asyncio
import socket
from typing import Dict, Optional, Set, List
from .socket_interfaces import IClientSession, ServerBase
from .packet_callbacks import PacketProcessor
from .packet_frame import PacketFrame, debug_print
from .tcp_protocol import TcpProtocol


class TcpClientSession(IClientSession):
    """TCP接続のクライアントセッションを表すクラス"""
    
    def __init__(self, writer: asyncio.StreamWriter, session_id: int, user_id: int = 0, group_id: int = 0, name: str = None):
        self._writer = writer
        self._session_id = session_id  # セッションID（接続ごとに一意）
        self._user_id = user_id        # ユーザーID（同一ユーザーから複数接続可能）
        self._group_id = group_id
        self._name = name
        self._is_alive = True
        
    @property
    def group_id(self) -> int:
        return self._group_id
        
    @group_id.setter
    def group_id(self, value: int) -> None:
        self._group_id = value
        
    @property
    def user_id(self) -> int:
        return self._user_id
        
    @user_id.setter
    def user_id(self, value: int) -> None:
        self._user_id = value
        
    @property
    def name(self) -> Optional[str]:
        return self._name
        
    @name.setter
    def name(self, value: Optional[str]) -> None:
        self._name = value
        
    @property
    def is_alive(self) -> bool:
        return self._is_alive and not self._writer.is_closing()
    
    @property
    def session_id(self) -> int:
        return self._session_id
        
    def close(self) -> None:
        """セッションを閉じる"""
        self._is_alive = False
        if not self._writer.is_closing():
            self._writer.close()
            
    def get_writer(self) -> asyncio.StreamWriter:
        """StreamWriterを取得する"""
        return self._writer


class TcpServer(ServerBase):
    """TCP通信を行うサーバークラス"""
    
    def __init__(self):
        super().__init__()
        self._sessions: Dict[int, TcpClientSession] = {}  # session_id -> TcpClientSession
        self._user_sessions: Dict[int, List[int]] = {}    # user_id -> List[session_id]
        self._server = None
        self._next_session_id = 1  # 新しいクライアントに割り当てるセッションID
        self._running = False
        self._processor = PacketProcessor(self)
        self._sessions_lock = asyncio.Lock()  # セッション管理用のロック
        
    @property
    def sessions(self) -> Dict[int, IClientSession]:
        return self._sessions
        
    async def start_async(self, port_number: int) -> None:
        """
        サーバーを開始する
        
        Args:
            port_number: リッスンするポート番号
        """
        if self._running:
            return
            
        self._running = True
        
        # サーバーの起動
        self._server = await asyncio.start_server(
            self._handle_client,
            '0.0.0.0',  # すべてのインターフェースでリッスン
            port_number
        )
        
        addr = self._server.sockets[0].getsockname()
        self.raise_log_message(f"サーバーを開始しました: {addr}")
        
        # サーバーの実行を開始
        async with self._server:
            await self._server.serve_forever()
    
    async def _register_user_session(self, session_id: int, user_id: int) -> None:
        """ユーザーとセッションの関連付けを登録する"""
        async with self._sessions_lock:
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            
            if session_id not in self._user_sessions[user_id]:
                self._user_sessions[user_id].append(session_id)
                debug_print(f"ユーザー {user_id} にセッション {session_id} を関連付けました")
            
    async def _unregister_user_session(self, session_id: int, user_id: int) -> None:
        """ユーザーとセッションの関連付けを解除する"""
        async with self._sessions_lock:
            if user_id in self._user_sessions and session_id in self._user_sessions[user_id]:
                self._user_sessions[user_id].remove(session_id)
                debug_print(f"ユーザー {user_id} からセッション {session_id} の関連付けを解除しました")
                
                # リストが空になったら辞書から削除
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]
                    debug_print(f"ユーザー {user_id} のセッションリストが空になったため削除しました")
                else:
                    debug_print(f"ユーザー {user_id} にはまだ {len(self._user_sessions[user_id])} 個のセッションが残っています")
                
    def _get_user_sessions(self, user_id: int) -> List[int]:
        """ユーザーIDに関連付けられたすべてのセッションIDのリストを取得する"""
        return self._user_sessions.get(user_id, []).copy()  # コピーを返すことで安全性を向上
            
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        クライアント接続を処理する
        
        Args:
            reader: クライアントからの読み込みストリーム
            writer: クライアントへの書き込みストリーム
        """
        # クライアントのアドレス情報を取得
        addr = writer.get_extra_info('peername')
        session_id = self._next_session_id
        self._next_session_id += 1
        
        # 初期値ではグループIDとユーザーIDは0とする
        session = TcpClientSession(writer, session_id, 0, 0, f"Client-{session_id}")
        
        async with self._sessions_lock:
            self._sessions[session_id] = session
        
        self.raise_log_message(f"クライアント接続: {addr}, SessionID: {session_id}")
        
        try:
            # 初期メッセージの送信 - セッションIDは含めない
            welcome_packet = PacketFrame.from_text(
                f"ようこそ！サーバーに接続しました。",
                destination_user_id=0,  # まだユーザーIDが不明なのでセッションIDで宛先指定しない
                source_user_id=0        # サーバーからのメッセージ
            )
            await TcpProtocol.send_packet(writer, welcome_packet)
            
            # クライアントからのデータを処理
            while session.is_alive:
                # 完全なパケットを待機
                packet = await TcpProtocol.receive_packet(reader)
                if packet is None:
                    break
                
                # 接続要求メッセージの処理（CONNECT:user_id:group_id形式）
                if packet.payload_type == 1:  # PlainText
                    message = packet.payload.decode('utf-8', errors='ignore')
                    if message.startswith("CONNECT:"):
                        try:
                            # メッセージからユーザーIDとグループIDを抽出
                            parts = message.split(":")
                            if len(parts) >= 3:
                                user_id = int(parts[1])
                                group_id = int(parts[2])
                                
                                # 旧ユーザーIDの関連付けを解除
                                if session.user_id != 0:
                                    await self._unregister_user_session(session_id, session.user_id)
                                
                                # 新しいユーザーID・グループIDを設定
                                session.user_id = user_id
                                session.group_id = group_id
                                
                                # ユーザーIDとセッションIDの関連付けを登録
                                await self._register_user_session(session_id, user_id)
                                
                                debug_print(f"クライアント情報更新 - SessionID: {session_id}, UserID: {user_id}, GroupID: {group_id}")
                        except (IndexError, ValueError) as e:
                            debug_print(f"CONNECT メッセージ解析エラー: {e}")
                
                # パケットの送信元情報を更新（現在のセッション情報を使用）
                if packet.source_user_id == 0xFFFF or packet.source_user_id == 0:
                    packet.source_user_id = session.user_id
                if packet.source_group_id == 0:
                    packet.source_group_id = session.group_id
                
                # 宛先に応じた処理
                if packet.destination_user_id == 0:
                    # サーバー宛てのパケット処理
                    debug_print(f"サーバー宛てパケット処理")
                    self._processor.process_packet(packet, f"Server-Session{session_id}")
                elif packet.destination_user_id == 0xFFFF:
                    # ブロードキャストまたはグループ指定
                    if packet.destination_group_id == 0xFFFF:
                        # ブロードキャスト
                        debug_print(f"ブロードキャスト転送")
                        await self._send_to_all_clients_except(session_id, packet)
                    else:
                        # グループ指定
                        debug_print(f"グループ {packet.destination_group_id} への転送")
                        await self._send_to_group(packet.destination_group_id, packet)
                    self.raise_log_message(f"[server from user {session.user_id}] 転送")
                else:
                    # 特定ユーザー指定
                    if packet.destination_group_id == 0xFFFF:
                        # ユーザーIDのみ指定
                        debug_print(f"ユーザーID {packet.destination_user_id} への転送")
                        await self._send_to_user(packet.destination_user_id, packet)
                    else:
                        # ユーザーIDとグループID両方指定
                        debug_print(f"ユーザーID {packet.destination_user_id}, グループID {packet.destination_group_id} への転送")
                        await self._send_to_user_and_group(packet.destination_user_id, packet.destination_group_id, packet)
                    self.raise_log_message(f"[server from user {session.user_id}] 転送")
                
        except asyncio.CancelledError:
            # タスクがキャンセルされた
            debug_print("クライアント処理タスクがキャンセルされました")
        except ConnectionResetError:
            # 接続がリセットされた
            debug_print("接続がリセットされました")
        except Exception as e:
            self.raise_log_message(f"クライアント処理中にエラーが発生: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # ユーザーとセッションの関連付けを解除
            if session.user_id != 0:
                await self._unregister_user_session(session_id, session.user_id)
            
            # クライアントとの接続を閉じる
            session.close()
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass
            
            # セッションを削除
            async with self._sessions_lock:
                if session_id in self._sessions:
                    del self._sessions[session_id]
                
            self.raise_log_message(f"クライアント切断: {addr}, SessionID: {session_id}")
    
    async def _send_to_all_clients_except(self, exclude_session_id: int, packet: PacketFrame) -> None:
        """指定したセッションID以外のすべてのクライアントにパケットを送信"""
        sessions_copy = []
        async with self._sessions_lock:
            sessions_copy = list(self._sessions.items())
            
        for session_id, session in sessions_copy:
            if session_id != exclude_session_id:
                await self._send_packet_to_client(session, packet)
    
    async def _send_to_group(self, group_id: int, packet: PacketFrame) -> None:
        """特定のグループに属するクライアントにパケットを送信"""
        sessions_copy = []
        async with self._sessions_lock:
            sessions_copy = list(self._sessions.values())
            
        for session in sessions_copy:
            if session.group_id == group_id:
                await self._send_packet_to_client(session, packet)
    
    async def _send_to_user(self, user_id: int, packet: PacketFrame) -> None:
        """特定のユーザーIDを持つすべてのクライアントにパケットを送信"""
        # ユーザーIDに関連付けられたすべてのセッションを取得
        session_ids = self._get_user_sessions(user_id)
        
        for session_id in session_ids:
            session = None
            async with self._sessions_lock:
                session = self._sessions.get(session_id)
            
            if session and session.is_alive:
                await self._send_packet_to_client(session, packet)
    
    async def _send_to_user_and_group(self, user_id: int, group_id: int, packet: PacketFrame) -> None:
        """特定のユーザーIDとグループIDを持つクライアントにパケットを送信"""
        # ユーザーIDに関連付けられたすべてのセッションを取得
        session_ids = self._get_user_sessions(user_id)
        
        for session_id in session_ids:
            session = None
            async with self._sessions_lock:
                session = self._sessions.get(session_id)
            
            if session and session.group_id == group_id and session.is_alive:
                await self._send_packet_to_client(session, packet)
            
    async def _send_packet_to_client(self, session: TcpClientSession, packet: PacketFrame) -> None:
        """
        クライアントにパケットを送信する
        
        Args:
            session: 送信先クライアントセッション
            packet: 送信するパケット
        """
        if not session.is_alive:
            debug_print(f"セッション {session.session_id} は既に切断されています")
            return
            
        writer = session.get_writer()
        try:
            await TcpProtocol.send_packet(writer, packet)
            debug_print(f"パケット送信成功: セッションID {session.session_id}")
        except Exception as e:
            self.raise_log_message(f"パケット送信中にエラーが発生: {e}, セッションID: {session.session_id}")
            # エラーが発生してもセッションは即座には閉じない
            # 次のパケット受信時に切断が検出される
            
    async def send_data_async(self, packet_data: PacketFrame) -> None:
        """
        すべてのクライアントまたは特定のクライアントにデータを送信する
        
        Args:
            packet_data: 送信するパケット
        """
        debug_print(f"send_data_async - 宛先ユーザーID: {packet_data.destination_user_id}, 宛先グループID: {packet_data.destination_group_id}")
        
        # 宛先に応じた処理
        if packet_data.destination_user_id != 0 and packet_data.destination_user_id != 0xFFFF:
            # 特定のユーザーへの送信
            await self._send_to_user(packet_data.destination_user_id, packet_data)
        elif packet_data.destination_group_id != 0 and packet_data.destination_group_id != 0xFFFF:
            # 特定のグループへの送信
            await self._send_to_group(packet_data.destination_group_id, packet_data)
        else:
            # すべてのクライアントへの送信
            sessions_copy = []
            async with self._sessions_lock:
                sessions_copy = list(self._sessions.values())
                
            for session in sessions_copy:
                await self._send_packet_to_client(session, packet_data)
                
    def stop(self) -> None:
        """サーバーを停止する"""
        if not self._running:
            return
            
        self._running = False
        
        # 全クライアントとの接続を閉じる
        # ロックを使用せずにセッションリストのコピーを作成
        sessions_copy = list(self._sessions.values())
            
        for session in sessions_copy:
            session.close()
            
        # サーバーを停止
        if self._server:
            self._server.close()

