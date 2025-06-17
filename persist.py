import sqlite3
import json
import functools
from datetime import datetime
from domains import NSFWNovel

def persist_novel_state(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        novel = self.state
        save(novel)
        return result
    return wrapper

def save(novel: NSFWNovel):
    db_path = 'novel_state.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nsfw_novel (
        id TEXT PRIMARY KEY,
        state_json TEXT,
        create_time TEXT,
        update_time TEXT,
        version INTEGER
    )''')
    now = datetime.now().isoformat()
    state_json = novel.model_dump_json()
    c.execute('SELECT id FROM nsfw_novel WHERE id=?', (novel.uuid,))
    row = c.fetchone()
    if row:
        c.execute('UPDATE nsfw_novel SET state_json=?, update_time=?, version=version+1 WHERE id=?',
                    (state_json, now, novel.uuid))
    else:
        c.execute('INSERT INTO nsfw_novel (id, state_json, create_time, update_time, version) VALUES (?, ?, ?, ?, ?)',
                    (novel.uuid, state_json, now, now, 1))
    conn.commit()
    conn.close()

def get_history_page(page: int, page_size: int):
    db_path = 'novel_state.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nsfw_novel (
        id TEXT PRIMARY KEY,
        state_json TEXT,
        create_time TEXT,
        update_time TEXT,
        version INTEGER
    )''')
    total_count = c.execute('SELECT COUNT(*) FROM nsfw_novel').fetchone()[0]
    rows = c.execute('SELECT id, state_json, create_time, update_time, version FROM nsfw_novel ORDER BY update_time DESC LIMIT ? OFFSET ?', (page_size, (page-1)*page_size)).fetchall()
    conn.close()
    return total_count, rows

def delete_novel(uuid: str):
    db_path = 'novel_state.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM nsfw_novel WHERE id=?', (uuid,))
    conn.commit()
    conn.close()
