#Py.HagLib.Socket/Socket/packet_callbacks.py

from typing import Callable, Dict, List, Optional, Tuple, Any
from PIL import Image
from .packet_frame import PacketFrame, PayloadType, debug_print


class IPacketCallbacks:
    """パケット処理のコールバックインターフェース"""
    def raise_first_message(self, message: str) -> None:
        """初期メッセージ受信時のコールバック"""
        pass
        
    def raise_binary(self, packet: PacketFrame) -> None:
        """バイナリデータ受信時のコールバック"""
        pass
        
    def raise_text(self, message: str, packet: PacketFrame) -> None:
        """テキストデータ受信時のコールバック"""
        pass
        
    def raise_image(self, image: Image.Image, packet: PacketFrame) -> None:
        """画像データ受信時のコールバック"""
        pass
        
    def raise_text_and_image(self, message: str, image: Image.Image, packet: PacketFrame) -> None:
        """テキストと画像を同時に受信した時のコールバック"""
        pass
        
    def raise_complex_data(self, complex_data: Tuple[List[str], List[Image.Image], List[bytes], PacketFrame]) -> None:
        """複合データ受信時のコールバック"""
        pass
        
    def raise_log_message(self, message: str) -> None:
        """ログメッセージ"""
        pass
        
    def raise_packet_frame(self, child_packet: PacketFrame, packet: PacketFrame) -> None:
        """PacketFrameを含むパケット受信時のコールバック"""
        pass
        
    def raise_requirement(self, complex_data: Tuple[List[str], List[Image.Image], List[bytes], PacketFrame]) -> None:
        """Requirementデータ受信時のコールバック"""
        pass


class PacketCallbacksBase(IPacketCallbacks):
    """コールバック実装用の基底クラス"""
    
    def __init__(self):
        # イベントハンドラリスト
        self._first_message_handlers = []
        self._binary_handlers = []
        self._text_handlers = []
        self._image_handlers = []
        self._text_and_image_handlers = []
        self._complex_data_handlers = []
        self._log_message_handlers = []
        self._packet_frame_handlers = []
        self._requirement_handlers = []

    # リスナー登録メソッド
    def add_first_message_listener(self, handler: Callable[[Any, str], None]) -> None:
        self._first_message_handlers.append(handler)
        
    def add_binary_listener(self, handler: Callable[[Any, PacketFrame], None]) -> None:
        self._binary_handlers.append(handler)
        
    def add_text_listener(self, handler: Callable[[Any, str, PacketFrame], None]) -> None:
        self._text_handlers.append(handler)
        
    def add_image_listener(self, handler: Callable[[Any, Image.Image, PacketFrame], None]) -> None:
        self._image_handlers.append(handler)
        
    def add_text_and_image_listener(self, handler: Callable[[Any, str, Image.Image, PacketFrame], None]) -> None:
        self._text_and_image_handlers.append(handler)
        
    def add_complex_data_listener(self, handler: Callable[[Any, Tuple[List[str], List[Image.Image], List[bytes], PacketFrame]], None]) -> None:
        self._complex_data_handlers.append(handler)
        
    def add_log_message_listener(self, handler: Callable[[str], None]) -> None:
        self._log_message_handlers.append(handler)
        
    def add_packet_frame_listener(self, handler: Callable[[Any, PacketFrame, PacketFrame], None]) -> None:
        self._packet_frame_handlers.append(handler)
        
    def add_requirement_listener(self, handler: Callable[[Any, Tuple[List[str], List[Image.Image], List[bytes], PacketFrame]], None]) -> None:
        self._requirement_handlers.append(handler)

    # イベント発火メソッド
    def raise_first_message(self, message: str) -> None:
        for handler in self._first_message_handlers:
            handler(self, message)
            
    def raise_binary(self, packet: PacketFrame) -> None:
        for handler in self._binary_handlers:
            handler(self, packet)
            
    def raise_text(self, message: str, packet: PacketFrame) -> None:
        for handler in self._text_handlers:
            handler(self, message, packet)
            
    def raise_image(self, image: Image.Image, packet: PacketFrame) -> None:
        for handler in self._image_handlers:
            handler(self, image, packet)
            
    def raise_text_and_image(self, message: str, image: Image.Image, packet: PacketFrame) -> None:
        for handler in self._text_and_image_handlers:
            handler(self, message, image, packet)
            
    def raise_complex_data(self, complex_data: Tuple[List[str], List[Image.Image], List[bytes], PacketFrame]) -> None:
        for handler in self._complex_data_handlers:
            handler(self, complex_data)
            
    def raise_log_message(self, message: str) -> None:
        for handler in self._log_message_handlers:
            handler(message)
            
    def raise_packet_frame(self, child_packet: PacketFrame, packet: PacketFrame) -> None:
        for handler in self._packet_frame_handlers:
            handler(self, child_packet, packet)
            
    def raise_requirement(self, complex_data: Tuple[List[str], List[Image.Image], List[bytes], PacketFrame]) -> None:
        for handler in self._requirement_handlers:
            handler(self, complex_data)


class PacketProcessor:
    """パケット処理クラス"""
    
    def __init__(self, callbacks_source: 'PacketCallbacksBase'):
        """
        PacketProcessorのコンストラクタ
        
        Args:
            callbacks_source: コールバックを提供するオブジェクト
        """
        self._callbacks_source = callbacks_source
        
    def process_packet(self, packet_data: PacketFrame, context: str = "") -> None:
        """
        受信したパケットを処理し、適切なイベントを発火する
        
        Args:
            packet_data: 処理するパケット
            context: コンテキスト情報（ログ用）
        """
        if packet_data is None:
            return
            
        if packet_data.payload_type == PayloadType.PlainText:
            # テキストメッセージの処理
            message = packet_data.message
            if message:
                # 接続要求メッセージの場合はテキストイベントを発火しない
                if message.startswith("CONNECT:"):
                    debug_print(f"接続要求メッセージを検出: {message}")
                    # ログメッセージとして記録するだけで、テキストイベントは発火しない
                    self._callbacks_source.raise_log_message(f"クライアント接続要求: {message}")
                else:
                    # 通常のテキストメッセージとして処理
                    self._callbacks_source.raise_text(message, packet_data)
                
        elif packet_data.payload_type == PayloadType.PngImage:
            # PNG画像の処理
            image = packet_data.to_image()
            if image:
                self._callbacks_source.raise_image(image, packet_data)
                
        elif packet_data.payload_type == PayloadType.TextAndPngImage:
            # テキストと画像の複合データの処理
            text, img = packet_data.to_text_and_image()
            if img:
                self._callbacks_source.raise_text_and_image(text or "", img, packet_data)
                
        elif packet_data.payload_type == PayloadType.Complex:
            # 複合データの処理
            self._callbacks_source.raise_complex_data(packet_data.to_complex())
            
        elif packet_data.payload_type == PayloadType.PacketFrame:
            # パケットデータの処理
            child_packet = packet_data.to_packet_frame()
            if child_packet:
                self._callbacks_source.raise_packet_frame(child_packet, packet_data)
            
        elif packet_data.payload_type == PayloadType.Requirement:
            # オーダーデータの処理
            self._callbacks_source.raise_requirement(packet_data.to_requirement())
            
        else:
            # バイナリデータの処理（デフォルト）
            self._callbacks_source.raise_binary(packet_data)
