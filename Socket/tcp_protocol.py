#Py.HagLib.Socket/Socket/tcp_protocol.py
import asyncio
import struct  # struct モジュールを追加
from typing import Optional, Tuple
from .packet_frame import PacketFrame, debug_print
from io import BytesIO


class TcpProtocol:
    """TCP通信でのパケット送受信を扱うプロトコルクラス"""

    @staticmethod
    async def send_packet(writer: asyncio.StreamWriter, packet: PacketFrame) -> None:
        """
        PacketFrameをTCPソケット経由で送信する
        
        Args:
            writer: 送信先のStreamWriter
            packet: 送信するPacketFrame
        """
        if writer is None or writer.is_closing():
            raise ConnectionError("送信先が閉じられています")
        
        try:
            # パケットをバイト列に変換
            data = packet.to_bytes()
            debug_print(f"送信パケット: サイズ={len(data)}, ヘッダー={data[:PacketFrame.HEADER_SIZE].hex()}")
            
            # データを送信
            writer.write(data)
            await writer.drain()
            
        except Exception as e:
            debug_print(f"パケット送信エラー: {e}")
            raise
    

    @staticmethod
    async def receive_packet(reader: asyncio.StreamReader) -> Optional[PacketFrame]:
        """
        TCPソケット経由でPacketFrameを受信する
        
        Args:
            reader: 受信元のStreamReader
            
        Returns:
            受信したPacketFrame、または接続が閉じられた場合はNone
        """
        try:
            # ヘッダーを読み込む
            header_data = await reader.readexactly(PacketFrame.HEADER_SIZE)
            if not header_data:
                debug_print("接続が閉じられました")
                return None
                
            debug_print(f"受信ヘッダー: {header_data.hex()}")
            
            # ヘッダーから必要なペイロードサイズを取得
            packet_header = struct.unpack(PacketFrame.HEADER_FORMAT, header_data)
            if packet_header[0] != PacketFrame.HEADER_MAGIC:
                debug_print(f"無効なマジック値: {packet_header[0]} != {PacketFrame.HEADER_MAGIC}")
                return None
                
            payload_size = packet_header[7]  # ヘッダーの8番目の要素がペイロードサイズ
            debug_print(f"ペイロードサイズ: {payload_size}")
            
            # ペイロードを読み込む
            payload_data = b''
            if payload_size > 0:
                try:
                    payload_data = await reader.readexactly(payload_size)
                    debug_print(f"ペイロード読み込み完了: {len(payload_data)}/{payload_size}")
                except asyncio.IncompleteReadError as e:
                    debug_print(f"ペイロード読み込み不完全: {len(e.partial)}/{payload_size}")
                    return None
                    
            # 完全なパケットデータを構築
            packet_data = header_data + payload_data
            
            # パケットを解析
            packet = PacketFrame.from_bytes(packet_data)
            if packet:
                debug_print(f"パケット受信完了: ペイロードサイズ={packet.payload_size}")
            else:
                debug_print("パケットの解析に失敗しました")
                
            return packet
            
        except asyncio.CancelledError:
            debug_print("受信タスクがキャンセルされました")
            return None
        except asyncio.IncompleteReadError:
            debug_print("接続が切断されました（IncompleteReadError）")
            return None
        except Exception as e:
            debug_print(f"パケット受信エラー: {e}")
            return None