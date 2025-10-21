# app/database.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# データベースファイルのパス
DB_PATH = Path(__file__).parent.parent / "conversations.db"

@contextmanager
def get_db():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """データベースの初期化（テーブル作成）"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 会話テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                conversation_tree TEXT NOT NULL
            )
        """)

        # インデックス作成
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_updated_at ON conversations(updated_at)
        """)

        # LINE用メッセージ履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # LINE用インデックス
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_user_id ON line_messages(user_id, created_at DESC)
        """)

        print("[DB] Database initialized")

def save_conversation(
    conversation_id: str,
    user_id: str,
    conversation_tree: Dict[str, Any],
    title: Optional[str] = None
) -> bool:
    """会話を保存"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # タイトルが指定されていない場合は最初のユーザーメッセージから生成
            if not title:
                # conversation_treeから最初のユーザーメッセージを探す
                try:
                    nodes = conversation_tree.get("nodes", {})
                    current_path = conversation_tree.get("currentPath", [])

                    for node_id in current_path[1:]:  # Skip root
                        node = nodes.get(str(node_id))
                        if node and node.get("message", {}).get("role") == "user":
                            content = node["message"]["content"]
                            title = content[:50] + ("..." if len(content) > 50 else "")
                            break

                    if not title:
                        title = "新しい会話"
                except Exception:
                    title = "新しい会話"

            # 既存の会話があるか確認
            cursor.execute(
                "SELECT id FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            exists = cursor.fetchone()

            tree_json = json.dumps(conversation_tree, ensure_ascii=False)

            if exists:
                # 更新
                cursor.execute("""
                    UPDATE conversations
                    SET conversation_tree = ?,
                        title = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (tree_json, title, conversation_id, user_id))
            else:
                # 新規作成
                cursor.execute("""
                    INSERT INTO conversations (id, user_id, title, conversation_tree)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, user_id, title, tree_json))

            return True
    except Exception as e:
        print(f"[DB] Error saving conversation: {e}")
        return False

def get_conversation(conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """会話を取得"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at, conversation_tree
                FROM conversations
                WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))

            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "conversation_tree": json.loads(row["conversation_tree"])
                }
            return None
    except Exception as e:
        print(f"[DB] Error getting conversation: {e}")
        return None

def list_conversations(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """ユーザーの会話一覧を取得"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                for row in rows
            ]
    except Exception as e:
        print(f"[DB] Error listing conversations: {e}")
        return []

def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """会話を削除"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM conversations
                WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))
            return cursor.rowcount > 0
    except Exception as e:
        print(f"[DB] Error deleting conversation: {e}")
        return False

def save_line_message(user_id: str, role: str, content: str) -> bool:
    """LINE用メッセージを保存"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO line_messages (user_id, role, content)
                VALUES (?, ?, ?)
            """, (user_id, role, content))
            return True
    except Exception as e:
        print(f"[DB] Error saving LINE message: {e}")
        return False

def get_line_conversation(user_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """LINE用の会話履歴を取得（最新N件）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content
                FROM line_messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()
            # 古い順に並び替えて返す
            return [
                {"role": row["role"], "content": row["content"]}
                for row in reversed(rows)
            ]
    except Exception as e:
        print(f"[DB] Error getting LINE conversation: {e}")
        return []

# アプリ起動時にデータベースを初期化
init_db()
