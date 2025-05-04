#
import asyncio
import sys
import os
import time
from typing import List
import argparse

# 以下はパッケージパスを調整する例です。実際の環境に合わせて変更してください
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#from Socket.tcp_server import TcpServer
#from Socket.tcp_client import TcpClient
#from Socket.packet_frame import PacketFrame
from tcp_server import TcpServer
from tcp_client import TcpClient
from packet_frame import PacketFrame
# ----------------------
# テスト用ハンドラー
# ----------------------

async def client_message_handler(client, message, packet):
    """クライアントがメッセージを受信したときのハンドラー"""
    print(f"クライアント (UserID: {client.user_id}, SessionID: {client.session_id}) がメッセージを受信: {message}")

# ----------------------
# サーバー実行関数
# ----------------------

async def run_server(port: int = 8888):
    """テスト用サーバーを実行"""
    server = TcpServer()
    server.name = "テストサーバー"
    
    # サーバーログを表示
    server.add_log_message_listener(lambda msg: print(f"[サーバー] {msg}"))
    
    # サーバー開始
    server_task = asyncio.create_task(server.start_async(port))
    print(f"サーバーを開始しました (ポート: {port})")
    
    return server, server_task

# ----------------------
# クライアント実行関数
# ----------------------

async def run_client(server_host: str, port: int, user_id: int, group_id: int, client_name: str):
    """テスト用クライアントを実行"""
    client = TcpClient()
    client.name = client_name
    
    # クライアントのハンドラーを設定
    client.add_log_message_listener(lambda msg: print(f"[{client_name}] {msg}"))
    client.add_text_listener(client_message_handler)
    
    # サーバーに接続
    await client.connect_async(server_host, port, user_id, group_id)
    print(f"{client_name} (UserID: {user_id}, GroupID: {group_id}) がサーバーに接続しました")
    
    return client

# ----------------------
# テスト関数
# ----------------------

async def test_multiple_connections():
    """複数の同一ユーザーIDからの接続テスト"""
    # サーバーを起動
    server, server_task = await run_server(8888)
    
    try:
        # 1秒待機 (サーバー安定化)
        await asyncio.sleep(1)
        
        # 同じユーザーIDを持つ複数のクライアントを作成
        clients = []
        
        # ユーザーID 100、グループID 1のクライアントを3つ作成
        clients.append(await run_client("localhost", 8888, 100, 1, "クライアント1-A"))
        await asyncio.sleep(0.5)
        
        clients.append(await run_client("localhost", 8888, 100, 1, "クライアント1-B"))
        await asyncio.sleep(0.5)
        
        clients.append(await run_client("localhost", 8888, 100, 1, "クライアント1-C"))
        await asyncio.sleep(0.5)
        
        # ユーザーID 200、グループID 2のクライアントを1つ作成
        clients.append(await run_client("localhost", 8888, 200, 2, "クライアント2"))
        await asyncio.sleep(0.5)
        
        # すべてのクライアント情報を表示
        print("\n接続されたクライアント情報:")
        for idx, client in enumerate(clients):
            print(f"クライアント{idx+1}: Name={client.name}, UserID={client.user_id}, GroupID={client.group_id}")
        
        print("\n--- テスト1: 特定ユーザー宛てのメッセージ送信 ---")
        print("クライアント2からユーザーID 100宛てにメッセージを送信（すべてのセッションで受信されるはず）")
        
        # クライアント2からユーザーID 100宛てのメッセージを送信
        message = f"これはユーザーID 100宛てのメッセージです。送信時刻: {time.strftime('%H:%M:%S')}"
        await clients[3].send_data_async(PacketFrame.from_text(
            message,
            destination_user_id=100,
            destination_group_id=0xFFFF  # グループIDは指定なし
        ))
        
        # 処理が完了するまで少し待機
        await asyncio.sleep(1)
        
        print("\n--- テスト2: 特定ユーザー・グループ宛てのメッセージ送信 ---")
        print("クライアント2からユーザーID 100、グループID 1宛てにメッセージを送信")
        
        # クライアント2からユーザーID 100、グループID 1宛てのメッセージを送信
        message = f"これはユーザーID 100、グループID 1宛てのメッセージです。送信時刻: {time.strftime('%H:%M:%S')}"
        await clients[3].send_data_async(PacketFrame.from_text(
            message,
            destination_user_id=100,
            destination_group_id=1
        ))
        
        # 処理が完了するまで少し待機
        await asyncio.sleep(1)
        
        print("\n--- テスト3: 同一ユーザーの複数クライアントからメッセージ送信 ---")
        print("クライアント1-Aからユーザー200宛てにメッセージを送信")
        
        # クライアント1-Aからユーザー200宛てのメッセージを送信
        message = f"これはクライアント1-AからユーザーID 200宛てのメッセージです。送信時刻: {time.strftime('%H:%M:%S')}"
        await clients[0].send_data_async(PacketFrame.from_text(
            message,
            destination_user_id=200,
            destination_group_id=0xFFFF
        ))
        
        # 少し待機
        await asyncio.sleep(1)
        
        # サーバーのセッション情報を表示
        print("\nサーバーのセッション情報:")
        for session_id, session in server.sessions.items():
            print(f"SessionID: {session_id}, UserID: {session.user_id}, GroupID: {session.group_id}, Name: {session.name}")
        
        # すべてのクライアントを切断
        print("\nすべてのクライアントを切断します...")
        for client in clients:
            client.disconnect()
        
        # 少し待機
        await asyncio.sleep(1)
        
    finally:
        # サーバーを停止
        print("サーバーを停止します...")
        server.stop()
        # タスクをキャンセル
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

# ----------------------
# メイン関数
# ----------------------

async def main():
    parser = argparse.ArgumentParser(description='TCP通信のマルチクライアントテスト')
    parser.add_argument('--test', choices=['multiple'], default='multiple', help='実行するテスト種別')
    
    args = parser.parse_args()
    
    if args.test == 'multiple':
        await test_multiple_connections()

if __name__ == "__main__":
    # asyncioのイベントループを実行
    asyncio.run(main())
