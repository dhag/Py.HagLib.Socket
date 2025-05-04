#Py.HagLib.Socket/Socket/packet_frame.py
import struct
from enum import IntEnum
from typing import List, Tuple, Optional, Dict, Any
from io import BytesIO
from PIL import Image


# デバッグ用のフラグ
DEBUG = True


def debug_print(message):
    """デバッグメッセージを出力"""
    if DEBUG:
        print(f"[DEBUG] {message}")


class PayloadType(IntEnum):
    """パケットのペイロードタイプを定義するEnum"""
    BinaryRaw = 0
    PlainText = 1  # 推奨
    PngImage = 8000
    TextAndPngImage = 8001
    Complex = 10000  # 推奨
    PacketFrame = 20000
    Requirement = 30000  # 推奨


class PacketFrameHelper:
    """PacketFrameのユーティリティメソッドを提供するヘルパークラス"""

    @staticmethod
    def list_to_byte_array(list_of_byte_arrays: List[bytes]) -> bytes:
        """
        複数のバイト配列を1つのバイト配列に変換する
        各配列の前に長さ情報(4バイト)を付加する
        """
        if not list_of_byte_arrays:
            return b''

        result = bytearray()
        for array in list_of_byte_arrays:
            # 配列のサイズを4バイトで格納
            result.extend(struct.pack('<I', len(array)))
            # 配列本体を格納
            result.extend(array)

        return bytes(result)

    @staticmethod
    def byte_array_to_list(byte_array: bytes) -> List[bytes]:
        """
        1つのバイト配列から複数のバイト配列に変換する
        各配列の前に付加されている長さ情報(4バイト)を使用して分割する
        """
        result = []
        if not byte_array:
            return result

        offset = 0
        while offset < len(byte_array):
            # 配列サイズを取得
            length = struct.unpack('<I', byte_array[offset:offset+4])[0]
            offset += 4

            # 指定サイズのbyte配列を取得
            single_array = byte_array[offset:offset+length]
            result.append(single_array)
            offset += length

        return result


class PacketFrame:
    """
    ネットワークパケットのヘッダー＋ペイロードを表現するクラス
    """
    HEADER_MAGIC = b'hag1'
    HEADER_FORMAT = '<4s4sIIIIII'  # シグネチャ(4バイト)、予約(4バイト)、送信先グループID(4バイト)、送信先ユーザーID(4バイト)、
                             # 送信元グループID(4バイト)、送信元ユーザーID(4バイト)、ペイロードタイプ(4バイト)、ペイロードサイズ(4バイト)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self,
                 destination_group_id: int = 0,
                 destination_user_id: int = 0,
                 source_group_id: int = 0,
                 source_user_id: int = 0xFFFF,
                 payload_type: PayloadType = PayloadType.BinaryRaw,
                 payload: bytes = b""):
        self.destination_group_id = destination_group_id
        self.destination_user_id = destination_user_id
        self.source_group_id = source_group_id
        self.source_user_id = source_user_id
        self.payload_type = payload_type
        self.payload = payload or b""

    @property
    def payload_size(self) -> int:
        """ペイロードのサイズを返す"""
        return len(self.payload)

    def to_bytes(self) -> bytes:
        """
        PacketFrame をバイト列にシリアライズする。ヘッダー + ペイロード。
        """
        reserved = b'\x00\x00\x00\x00'  # 予約領域を4バイトのゼロで埋める
        header = struct.pack(
            self.HEADER_FORMAT,
            self.HEADER_MAGIC,
            reserved,
            self.destination_group_id,
            self.destination_user_id,
            self.source_group_id,
            self.source_user_id,
            int(self.payload_type),
            self.payload_size
        )
        debug_print(f"シリアライズ: ヘッダーサイズ={len(header)}, マジック={self.HEADER_MAGIC}, " + 
                    f"送信先グループID={self.destination_group_id}, 送信先ユーザーID={self.destination_user_id}, " +
                    f"送信元グループID={self.source_group_id}, 送信元ユーザーID={self.source_user_id}, " +
                    f"ペイロードタイプ={self.payload_type}, ペイロードサイズ={self.payload_size}")
        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['PacketFrame']:
        """
        バイト列から PacketFrame を逆シリアライズする。
        data はヘッダー(32バイト) + payload_size バイト以上を含む必要がある。
        """
        if len(data) < cls.HEADER_SIZE:
            debug_print(f"データサイズ不足: {len(data)} < {cls.HEADER_SIZE}")
            return None
            
        try:
            unpacked = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
            magic, reserved, dest_grp, dest_usr, src_grp, src_usr, ptype, psize = unpacked
            
            debug_print(f"デシリアライズ: マジック={magic}, " + 
                        f"送信先グループID={dest_grp}, 送信先ユーザーID={dest_usr}, " +
                        f"送信元グループID={src_grp}, 送信元ユーザーID={src_usr}, " +
                        f"ペイロードタイプ={ptype}, ペイロードサイズ={psize}")
                        
            if magic != cls.HEADER_MAGIC:
                debug_print(f"無効なマジック値: {magic} != {cls.HEADER_MAGIC}")
                return None
                
            # データに含まれるペイロードサイズをチェック
            if len(data) < cls.HEADER_SIZE + psize:
                debug_print(f"ペイロードサイズ不足: {len(data) - cls.HEADER_SIZE} < {psize}")
                return None
                
            payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + psize]
                
            return cls(
                destination_group_id=dest_grp,
                destination_user_id=dest_usr,
                source_group_id=src_grp,
                source_user_id=src_usr,
                payload_type=PayloadType(ptype),
                payload=payload
            )
        except Exception as e:
            debug_print(f"デシリアライズエラー: {e}")
            return None

    @classmethod
    def from_text(cls, message: str,
                  destination_group_id: int = 0,
                  destination_user_id: int = 0,
                  source_group_id: int = 0,
                  source_user_id: int = 0xFFFF) -> 'PacketFrame':
        """テキストメッセージからPacketFrameを作成する"""
        payload = message.encode('utf-8')
        return cls(destination_group_id, destination_user_id,
                   source_group_id, source_user_id,
                   PayloadType.PlainText, payload)

    @classmethod
    def from_bytes_raw(cls, raw: bytes,
                       destination_group_id: int = 0,
                       destination_user_id: int = 0,
                       source_group_id: int = 0,
                       source_user_id: int = 0xFFFF) -> 'PacketFrame':
        """バイナリデータからPacketFrameを作成する"""
        return cls(destination_group_id, destination_user_id,
                   source_group_id, source_user_id,
                   PayloadType.BinaryRaw, raw)

    @classmethod
    def from_image(cls, image: Image.Image,
                   destination_group_id: int = 0,
                   destination_user_id: int = 0,
                   source_group_id: int = 0,
                   source_user_id: int = 0xFFFF) -> 'PacketFrame':
        """画像からPacketFrameを作成する"""
        buf = BytesIO()
        image.save(buf, format='PNG')
        payload = buf.getvalue()
        return cls(destination_group_id, destination_user_id,
                   source_group_id, source_user_id,
                   PayloadType.PngImage, payload)

    @classmethod
    def from_text_and_image(cls, text: str, image: Image.Image,
                            destination_group_id: int = 0,
                            destination_user_id: int = 0,
                            source_group_id: int = 0,
                            source_user_id: int = 0xFFFF) -> 'PacketFrame':
        """テキストと画像からPacketFrameを作成する"""
        text_data = text.encode('utf-8')
        
        buf = BytesIO()
        image.save(buf, format='PNG')
        image_data = buf.getvalue()
        
        payload = PacketFrameHelper.list_to_byte_array([text_data, image_data])
        
        return cls(destination_group_id, destination_user_id,
                   source_group_id, source_user_id,
                   PayloadType.TextAndPngImage, payload)

    @classmethod
    def from_complex(cls, 
                     texts: Optional[List[str]] = None,
                     images: Optional[List[Image.Image]] = None,
                     binary_data: Optional[List[bytes]] = None,
                     destination_group_id: int = 0,
                     destination_user_id: int = 0,
                     source_group_id: int = 0,
                     source_user_id: int = 0xFFFF) -> 'PacketFrame':
        """複合データからPacketFrameを作成する"""
        texts = texts or []
        images = images or []
        binary_data = binary_data or []
        
        # テキストをバイト配列に変換
        text_bytes = [text.encode('utf-8') for text in texts]
        
        # 画像をPNGフォーマットのバイト配列に変換
        image_bytes = []
        for img in images:
            buf = BytesIO()
            img.save(buf, format='PNG')
            image_bytes.append(buf.getvalue())
        
        # カウント情報を作成
        counts = struct.pack('<III', len(text_bytes), len(image_bytes), len(binary_data))
        
        # すべてのデータを1つのリストにまとめる
        all_data = [counts] + text_bytes + image_bytes + binary_data
        
        # リストをバイト配列に変換
        payload = PacketFrameHelper.list_to_byte_array(all_data)
        
        return cls(destination_group_id, destination_user_id,
                   source_group_id, source_user_id,
                   PayloadType.Complex, payload)

    def to_text(self) -> str:
        """PlainTextタイプのペイロードからテキストを取り出す"""
        if self.payload_type == PayloadType.PlainText:
            return self.payload.decode('utf-8', errors='ignore')
        elif self.payload_type == PayloadType.TextAndPngImage:
            parts = PacketFrameHelper.byte_array_to_list(self.payload)
            if len(parts) >= 1:
                return parts[0].decode('utf-8', errors='ignore')
        elif self.payload_type == PayloadType.Complex:
            texts, _, _, _ = self.to_complex()
            if texts:
                return texts[0]
        return ''

    def to_image(self) -> Optional[Image.Image]:
        """画像を取り出す"""
        if self.payload_type == PayloadType.PngImage:
            return Image.open(BytesIO(self.payload))
        elif self.payload_type == PayloadType.TextAndPngImage:
            parts = PacketFrameHelper.byte_array_to_list(self.payload)
            if len(parts) >= 2:
                return Image.open(BytesIO(parts[1]))
        elif self.payload_type == PayloadType.Complex:
            _, images, _, _ = self.to_complex()
            if images:
                return images[0]
        return None

    def to_text_and_image(self) -> Tuple[Optional[str], Optional[Image.Image]]:
        """テキストと画像を取り出す"""
        text = None
        image = None
        
        if self.payload_type == PayloadType.TextAndPngImage:
            parts = PacketFrameHelper.byte_array_to_list(self.payload)
            if len(parts) >= 1:
                text = parts[0].decode('utf-8', errors='ignore')
            if len(parts) >= 2:
                image = Image.open(BytesIO(parts[1]))
        elif self.payload_type == PayloadType.PlainText:
            text = self.payload.decode('utf-8', errors='ignore')
        elif self.payload_type == PayloadType.PngImage:
            image = Image.open(BytesIO(self.payload))
        elif self.payload_type == PayloadType.Complex:
            texts, images, _, _ = self.to_complex()
            if texts:
                text = texts[0]
            if images:
                image = images[0]
                
        return text, image

    def to_complex(self) -> Tuple[List[str], List[Image.Image], List[bytes], 'PacketFrame']:
        """複合データを取り出す"""
        if self.payload_type != PayloadType.Complex:
            return [], [], [], self
            
        parts = PacketFrameHelper.byte_array_to_list(self.payload)
        if not parts:
            return [], [], [], self
            
        # カウント情報を取得
        counts_data = parts[0]
        text_count, image_count, binary_count = struct.unpack('<III', counts_data)
        
        all_items = parts[1:]
        current_index = 0
        
        # テキストを取り出す
        texts = []
        for i in range(text_count):
            if current_index < len(all_items):
                texts.append(all_items[current_index].decode('utf-8', errors='ignore'))
                current_index += 1
            
        # 画像を取り出す
        images = []
        for i in range(image_count):
            if current_index < len(all_items):
                images.append(Image.open(BytesIO(all_items[current_index])))
                current_index += 1
            
        # バイナリデータを取り出す
        binaries = []
        for i in range(binary_count):
            if current_index < len(all_items):
                binaries.append(all_items[current_index])
                current_index += 1
                
        return texts, images, binaries, self

    def to_packet_frame(self) -> Optional['PacketFrame']:
        """PacketFrameタイプのペイロードからPacketFrameを取り出す"""
        if self.payload_type == PayloadType.PacketFrame:
            return PacketFrame.from_bytes(self.payload)
        return None

    def to_requirement(self) -> Tuple[List[str], List[Image.Image], List[bytes], 'PacketFrame']:
        """Requirementタイプのペイロードからデータを取り出す"""
        if self.payload_type == PayloadType.Requirement:
            # Complexと同じ形式だが、意味が異なる
            return self.to_complex()
        return [], [], [], self

    def to_base64_image(self, with_header: bool = True) -> str:
        """画像をBase64文字列として取り出す"""
        import base64
        
        image_data = None
        
        if self.payload_type == PayloadType.PngImage:
            image_data = self.payload
        elif self.payload_type == PayloadType.TextAndPngImage:
            parts = PacketFrameHelper.byte_array_to_list(self.payload)
            if len(parts) >= 2:
                image_data = parts[1]
        elif self.payload_type == PayloadType.Complex:
            _, images, _, _ = self.to_complex()
            if images:
                buf = BytesIO()
                images[0].save(buf, format='PNG')
                image_data = buf.getvalue()
                
        if image_data:
            b64 = base64.b64encode(image_data).decode('ascii')
            if with_header:
                return f"data:image/png;base64,{b64}"
            return b64
            
        return ""

    @staticmethod
    def convert_base64_string_to_image(base64_data: str, is_with_header: bool = True) -> Image.Image:
        """Base64文字列から画像を生成する"""
        import base64
        
        # ヘッダーを削除
        if is_with_header and ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
            
        # バイト配列に変換
        image_bytes = base64.b64decode(base64_data)
        
        # 画像オブジェクトに変換
        return Image.open(BytesIO(image_bytes))

    @property
    def message(self) -> str:
        """メッセージを取得する（文字列表現）"""
        return self.to_text()