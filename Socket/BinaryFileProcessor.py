#Py.HagLib.Socket/Socket/BinaryFileProcessor.py
import tempfile
import os
import shutil
from typing import List, Tuple, Dict, Optional
import uuid

class BinaryFileProcessor:
    """
    バイナリデータとファイル名を処理するクラス
    一時ファイルの管理と操作を行う
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初期化メソッド
        
        Args:
            temp_dir: 一時ファイルを保存するディレクトリ。Noneの場合はシステムのデフォルト一時ディレクトリを使用
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.file_mappings: Dict[str, Tuple[str, str]] = {}  # ID -> (temp_path, original_filename)
        
        # 一時ディレクトリが存在しない場合は作成
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def process_files(self, binary_data_list: List[bytes], original_filenames: List[str]) -> List[str]:
        """
        バイナリデータとオリジナルファイル名のリストを処理し、
        一時ファイルを作成してファイルIDのリストを返す
        
        Args:
            binary_data_list: バイナリデータのリスト
            original_filenames: オリジナルファイル名のリスト
        
        Returns:
            ファイルIDのリスト
        """
        if len(binary_data_list) != len(original_filenames):
            raise ValueError("バイナリデータとファイル名の数が一致しません")
        
        file_ids = []
        
        for binary_data, original_filename in zip(binary_data_list, original_filenames):
            file_id = self._create_temp_file(binary_data, original_filename)
            file_ids.append(file_id)
        
        return file_ids
    
    def _create_temp_file(self, binary_data: bytes, original_filename: str) -> str:
        """
        バイナリデータを一時ファイルに書き込み、ファイルIDを返す
        
        Args:
            binary_data: バイナリデータ
            original_filename: オリジナルファイル名
        
        Returns:
            ファイルID
        """
        # ファイルIDを生成
        file_id = str(uuid.uuid4())
        
        # 元のファイル名から拡張子を取得
        _, ext = os.path.splitext(original_filename)
        
        # 一時ファイルパスを生成
        temp_filename = f"{file_id}{ext}"
        temp_path = os.path.join(self.temp_dir, temp_filename)
        
        # バイナリデータをファイルに書き込む
        with open(temp_path, "wb") as f:
            f.write(binary_data)
        
        # マッピング情報を保存
        self.file_mappings[file_id] = (temp_path, original_filename)
        
        return file_id
    
    def get_file_info(self, file_id: str) -> Tuple[str, str]:
        """
        ファイルIDから一時ファイルパスとオリジナルファイル名を取得
        
        Args:
            file_id: ファイルID
        
        Returns:
            (一時ファイルパス, オリジナルファイル名)のタプル
        """
        if file_id not in self.file_mappings:
            raise KeyError(f"ファイルID '{file_id}' は存在しません")
        
        return self.file_mappings[file_id]
    
    def get_all_file_info(self) -> List[Tuple[str, str]]:
        """
        すべてのファイル情報を取得
        
        Returns:
            (一時ファイルパス, オリジナルファイル名)のタプルのリスト
        """
        return list(self.file_mappings.values())


    def process_data_sets(self, data_sets: List[Tuple[str, bytes]]) -> List[Tuple[str, str]]:
        """
        (ファイル名, バイナリデータ)のタプルリストを処理し、
        (一時ファイルパス, 元のファイル名)のタプルリストを返す
        
        Args:
            data_sets: (ファイル名, バイナリデータ)のタプルリスト
        
        Returns:
            (一時ファイルパス, 元のファイル名)のタプルリスト
        """
        result = []
        file_ids = []
        
        for original_filename, binary_data in data_sets:
            # 一時ファイルの作成
            file_id = self._create_temp_file(binary_data, original_filename)
            file_ids.append(file_id)
            
            # ファイル情報を取得
            temp_path, _ = self.file_mappings[file_id]
            
            # 結果リストに追加
            result.append((temp_path, original_filename))
        
        return result
    
    def remove_file(self, file_id: str) -> bool:
        """
        指定されたファイルIDの一時ファイルを削除
        
        Args:
            file_id: ファイルID
        
        Returns:
            削除が成功したかどうか
        """
        if file_id not in self.file_mappings:
            return False
        
        temp_path, _ = self.file_mappings[file_id]
        
        try:
            os.remove(temp_path)
            del self.file_mappings[file_id]
            return True
        except OSError:
            return False
    
    def cleanup(self) -> None:
        """
        すべての一時ファイルを削除
        """
        for file_id in list(self.file_mappings.keys()):
            self.remove_file(file_id)
    
    def __del__(self):
        """
        デストラクタ: インスタンスが破棄される際に一時ファイルをクリーンアップ
        """
        self.cleanup()
"""
# 使用例
def example_usage():
    # バイナリデータとファイル名のサンプル
    binary_data_list = [b"sample data 1", b"sample data 2"]
    original_filenames = ["document.txt", "image.jpg"]
    
    # プロセッサーのインスタンス化
    processor = BinaryFileProcessor()
    
    try:
        # ファイル処理
        file_ids = processor.process_files(binary_data_list, original_filenames)
        print(f"処理したファイルID: {file_ids}")
        
        # ファイル情報の取得
        for file_id in file_ids:
            temp_path, original_name = processor.get_file_info(file_id)
            print(f"ID: {file_id}, パス: {temp_path}, 元の名前: {original_name}")
            
            # ファイルを使った処理
            with open(temp_path, "rb") as f:
                content = f.read()
                print(f"ファイル内容: {content}")
    
    finally:
        # クリーンアップ (明示的に呼び出す場合)
        processor.cleanup()

# Gradioと組み合わせた使用例
def gradio_integration():
    import gradio as gr
    
    processor = BinaryFileProcessor()
    
    def process_uploads(binary_files, filenames):
        file_ids = processor.process_files(binary_files, filenames)
        results = []
        
        for file_id in file_ids:
            temp_path, original_name = processor.get_file_info(file_id)
            file_size = os.path.getsize(temp_path)
            results.append(f"{original_name}: {file_size} バイト")
        
        return results
    
    with gr.Blocks() as demo:
        # 実際の実装はGradioの仕様に合わせて調整する必要があります
        # このコードは概念的な例です
        binary_input = gr.File(file_count="multiple")
        output = gr.JSON()
        button = gr.Button("処理")
        button.click(fn=process_uploads, inputs=[binary_input], outputs=output)
    
    return demo

if __name__ == "__main__":
    example_usage()

# すべてのファイル情報を取得
#all_files = processor.get_all_file_info()  # (temp_path, original_filename)のリストを返す

# 使用例
def extract_data_sets(
    string_list: list[str], 
    binary_list: list[bytes], 
    start_string_index: int, 
    start_binary_index: int, 
    num_sets: int
) -> list[tuple[str, bytes]]:
    
    文字列リストとバイナリデータリストから指定範囲のデータセットを取り出す
    
    Args:
        string_list: 文字列のリスト
        binary_list: バイナリデータのリスト
        start_string_index: 文字列リストの開始インデックス
        start_binary_index: バイナリリストの開始インデックス
        num_sets: 取り出すセットの数
    
    Returns:
        (文字列, バイナリデータ)のタプルのリスト
    
    # 入力チェック
    if start_string_index < 0 or start_string_index >= len(string_list):
        raise ValueError(f"文字列リストの開始インデックスが範囲外です: {start_string_index}")
    
    if start_binary_index < 0 or start_binary_index >= len(binary_list):
        raise ValueError(f"バイナリリストの開始インデックスが範囲外です: {start_binary_index}")
    
    # 取り出す要素数の調整
    end_string_index = min(start_string_index + num_sets, len(string_list))
    end_binary_index = min(start_binary_index + num_sets, len(binary_list))
    
    # 実際に取り出せるセット数
    actual_sets = min(end_string_index - start_string_index, end_binary_index - start_binary_index)
    
    # 結果リストの作成
    result = []
    for i in range(actual_sets):
        string_item = string_list[start_string_index + i]
        binary_item = binary_list[start_binary_index + i]
        result.append((string_item, binary_item))
    
    return result



def example_with_data_sets():
    # サンプルデータ
    filenames = ["file1.txt", "file2.jpg", "file3.pdf", "file4.docx", "file5.png"]
    binary_data = [b"data0", b"data1", b"data2", b"data3", b"data4"]
    
    # 特定の範囲からデータセットを取り出す
    data_sets = extract_data_sets(filenames, binary_data, 1, 2, 3)#ファイル名は1番目、バイナリは２番目から３個取り出す
    
    # プロセッサーのインスタンス化
    processor = BinaryFileProcessor()
    
    try:
        # データセットを処理
        file_tuples = processor.process_data_sets(data_sets)
        
        # 結果の表示
        for temp_path, original_name in file_tuples:
            file_size = os.path.getsize(temp_path)
            print(f"元のファイル名: {original_name}, 一時ファイルパス: {temp_path}, サイズ: {file_size} バイト")
            
            # ファイルを使った処理
            with open(temp_path, "rb") as f:
                content = f.read()
                print(f"ファイル内容: {content}")
    
    finally:
        # クリーンアップ
        processor.cleanup()



"""
