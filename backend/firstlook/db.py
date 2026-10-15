"""Small, explicit SQLite migrations; all application data stays local."""

import os
import sqlite3
from pathlib import Path

MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS setting (
      key TEXT PRIMARY KEY, value TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    """,
    "CREATE TABLE company (\n id TEXT PRIMARY KEY,name TEXT NOT NULL,domain TEXT NOT NULL,platform TEXT NOT NULL,\n token TEXT NOT NULL,tags TEXT NOT NULL DEFAULT '[]',size TEXT NOT NULL DEFAULT 'unknown',\n verified INTEGER NOT NULL DEFAULT 0,user_tags INTEGER NOT NULL DEFAULT 0,\n last_crawled TEXT,last_success TEXT,consecutive_failures INTEGER NOT NULL DEFAULT 0,\n hit_rate REAL NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP\n);\nCREATE TABLE job (\n id INTEGER PRIMARY KEY,company_id TEXT NOT NULL REFERENCES company(id),external_id TEXT NOT NULL,\n title TEXT NOT NULL,apply_url TEXT NOT NULL,locations TEXT NOT NULL,remote INTEGER NOT NULL DEFAULT 0,\n department TEXT NOT NULL DEFAULT '',employment_type TEXT NOT NULL DEFAULT '',posted_at TEXT,\n description_html TEXT NOT NULL DEFAULT '',description TEXT NOT NULL,compensation TEXT NOT NULL DEFAULT '{}',\n content_hash TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,\n missing_count INTEGER NOT NULL DEFAULT 0,closed_detected_at TEXT,starred INTEGER NOT NULL DEFAULT 0,\n touched INTEGER NOT NULL DEFAULT 0,duplicate_of INTEGER REFERENCES job(id),ghost INTEGER NOT NULL DEFAULT 0,\n created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(company_id,external_id)\n);\nCREATE TRIGGER immutable_first_seen BEFORE UPDATE OF first_seen ON job\n WHEN OLD.first_seen != NEW.first_seen BEGIN SELECT RAISE(ABORT,'first_seen is immutable'); END;\nCREATE TABLE job_extract(job_id INTEGER PRIMARY KEY REFERENCES job(id),data TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE job_embedding(job_id INTEGER PRIMARY KEY REFERENCES job(id),model TEXT NOT NULL,content_hash TEXT NOT NULL,vector TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE crawl_run(id INTEGER PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT,counts INTEGER NOT NULL DEFAULT 0,bytes INTEGER NOT NULL DEFAULT 0,duration REAL NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE crawl_result(id INTEGER PRIMARY KEY,run_id INTEGER REFERENCES crawl_run(id),company_id TEXT REFERENCES company(id),status TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,bytes INTEGER NOT NULL DEFAULT 0,duration REAL NOT NULL DEFAULT 0,error TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE profile(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE match_feedback(id INTEGER PRIMARY KEY,job_id INTEGER REFERENCES job(id),label INTEGER NOT NULL,features TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE bank_entry(id TEXT PRIMARY KEY,data TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE resume_variant(id INTEGER PRIMARY KEY,job_id INTEGER REFERENCES job(id),cache_key TEXT NOT NULL,template TEXT NOT NULL DEFAULT 'classic',ready INTEGER NOT NULL DEFAULT 0,used INTEGER NOT NULL DEFAULT 0,pdf_path TEXT,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE variant_line(id INTEGER PRIMARY KEY,variant_id INTEGER NOT NULL REFERENCES resume_variant(id),bank_entry_id TEXT REFERENCES bank_entry(id),source_index INTEGER NOT NULL,original TEXT NOT NULL,text TEXT NOT NULL,suggestion TEXT,status TEXT NOT NULL DEFAULT 'original',position INTEGER NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE application(id INTEGER PRIMARY KEY,job_id INTEGER REFERENCES job(id),variant_id INTEGER REFERENCES resume_variant(id),state TEXT NOT NULL DEFAULT 'saved',notes TEXT NOT NULL DEFAULT '',contacts TEXT NOT NULL DEFAULT '',referral INTEGER NOT NULL DEFAULT 0,applied_at TEXT,response_at TEXT,minutes REAL NOT NULL DEFAULT 0,field_count INTEGER NOT NULL DEFAULT 0,has_essay INTEGER NOT NULL DEFAULT 0,confirmation TEXT,screenshot TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE application_field(id INTEGER PRIMARY KEY,application_id INTEGER NOT NULL REFERENCES application(id),name TEXT NOT NULL,value TEXT NOT NULL,sensitive INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE application_event(id INTEGER PRIMARY KEY,application_id INTEGER NOT NULL REFERENCES application(id),state TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE llm_call(id INTEGER PRIMARY KEY,feature TEXT NOT NULL,model TEXT NOT NULL,job_id INTEGER REFERENCES job(id),run_id TEXT NOT NULL,input_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,estimated_cost_cents INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'reserved',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE cache(key TEXT PRIMARY KEY,value TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE INDEX jobs_company ON job(company_id);\nCREATE INDEX jobs_open ON job(closed_detected_at,duplicate_of);\n",
]


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    target = str(path or os.environ.get("FIRSTLOOK_DB", ".firstlook/firstlook.db"))
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    for number, migration in enumerate(MIGRATIONS, 1):
        if number > version:
            db.executescript(f"BEGIN;\n{migration}\nPRAGMA user_version={number};\nCOMMIT;")
    return db
