from pathlib import Path

from .helpers import make_registry, run_command, write_file


def test_sqlite_schema_and_query_task(project: Path, stats):
    registry = make_registry(project, stats)
    write_file(
        registry,
        "schema.sql",
        "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE);\n"
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, total INTEGER NOT NULL);\n",
    )
    write_file(
        registry,
        "seed.sql",
        "INSERT INTO users (email) VALUES ('ada@example.com');\n"
        "INSERT INTO orders (user_id, total) VALUES (1, 1200), (1, 800);\n",
    )
    write_file(
        registry,
        "report.py",
        "import sqlite3\n\n"
        "connection = sqlite3.connect('shop.db')\n"
        "connection.executescript(open('schema.sql').read())\n"
        "connection.executescript(open('seed.sql').read())\n"
        "connection.commit()\n"
        "row = connection.execute(\n"
        "    'SELECT users.email, SUM(orders.total) FROM users '\n"
        "    'JOIN orders ON orders.user_id = users.id GROUP BY users.id'\n"
        ").fetchone()\n"
        "print(f'{row[0]} {row[1]}')\n",
    )
    output = run_command(registry, "python3 report.py")
    assert "ada@example.com 2000" in output
