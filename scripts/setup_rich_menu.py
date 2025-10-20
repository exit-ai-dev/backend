"""
LINE Rich Menu セットアップスクリプト
トーク画面下部にLIFFアプリを開くボタンを追加
"""
import os
import json
import requests
from dotenv import load_dotenv, find_dotenv

# 環境変数を読み込む
load_dotenv(find_dotenv(filename=".env", usecwd=True))

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LIFF_APP_URL = os.getenv("LIFF_APP_URL")

if not CHANNEL_ACCESS_TOKEN:
    print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
    exit(1)

if not LIFF_APP_URL:
    print("❌ LIFF_APP_URL が設定されていません")
    exit(1)

# LINE Messaging API エンドポイント
API_BASE = "https://api.line.me/v2/bot"
HEADERS = {
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def create_rich_menu():
    """Rich Menuを作成"""
    url = f"{API_BASE}/richmenu"

    # Rich Menu の設定
    rich_menu_data = {
        "size": {
            "width": 2500,
            "height": 843
        },
        "selected": True,
        "name": "EXIT GPT Menu",
        "chatBarText": "メニュー",
        "areas": [
            {
                "bounds": {
                    "x": 0,
                    "y": 0,
                    "width": 1250,
                    "height": 843
                },
                "action": {
                    "type": "uri",
                    "uri": LIFF_APP_URL
                }
            },
            {
                "bounds": {
                    "x": 1250,
                    "y": 0,
                    "width": 1250,
                    "height": 843
                },
                "action": {
                    "type": "message",
                    "text": "ヘルプ"
                }
            }
        ]
    }

    response = requests.post(url, headers=HEADERS, json=rich_menu_data)

    if response.status_code == 200:
        rich_menu_id = response.json()["richMenuId"]
        print(f"✅ Rich Menu作成成功: {rich_menu_id}")
        return rich_menu_id
    else:
        print(f"❌ Rich Menu作成失敗: {response.status_code}")
        print(response.text)
        return None


def upload_rich_menu_image(rich_menu_id):
    """Rich Menu画像をアップロード（簡易版：単色背景）"""
    # 画像が必要な場合は、ここで画像をアップロード
    # 今回はスキップ（画像なしでも動作します）
    print("⚠️  Rich Menu画像のアップロードはスキップされました")
    print("   画像を追加する場合は、LINE Developers Consoleから手動でアップロードしてください")


def set_default_rich_menu(rich_menu_id):
    """デフォルトのRich Menuとして設定"""
    url = f"{API_BASE}/user/all/richmenu/{rich_menu_id}"

    response = requests.post(url, headers=HEADERS)

    if response.status_code == 200:
        print(f"✅ デフォルトRich Menu設定成功")
        return True
    else:
        print(f"❌ デフォルトRich Menu設定失敗: {response.status_code}")
        print(response.text)
        return False


def list_rich_menus():
    """現在のRich Menuリストを表示"""
    url = f"{API_BASE}/richmenu/list"

    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        menus = response.json().get("richmenus", [])
        print(f"\n📋 現在のRich Menuリスト ({len(menus)}件):")
        for menu in menus:
            print(f"  - {menu['name']} (ID: {menu['richMenuId']})")
        return menus
    else:
        print(f"❌ Rich Menuリスト取得失敗: {response.status_code}")
        return []


def main():
    print("=== LINE Rich Menu セットアップ ===\n")

    # 既存のRich Menuを確認
    existing_menus = list_rich_menus()

    # Rich Menuを作成
    print("\n🔧 Rich Menuを作成中...")
    rich_menu_id = create_rich_menu()

    if not rich_menu_id:
        print("\n❌ Rich Menuの作成に失敗しました")
        return

    # デフォルトとして設定
    print("\n🔧 デフォルトRich Menuとして設定中...")
    set_default_rich_menu(rich_menu_id)

    print("\n✅ セットアップ完了！")
    print(f"\nLIFFアプリURL: {LIFF_APP_URL}")
    print("\n次の手順:")
    print("1. LINE Developers Console (https://developers.line.biz/console/) を開く")
    print("2. 該当チャネルの「Messaging API」→「Rich menu」セクションを開く")
    print(f"3. Rich Menu ID: {rich_menu_id} に画像をアップロード")
    print("   推奨サイズ: 2500 x 843 px")
    print("   左半分: 「チャットを開く」ボタン")
    print("   右半分: 「ヘルプ」ボタン")
    print("\n画像がなくても動作しますが、ユーザーにはボタンの境界が見えません。")


if __name__ == "__main__":
    main()
