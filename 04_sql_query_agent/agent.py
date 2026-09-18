"""Natural-language querying for SQLite databases.

The agent generates SQL with an OpenAI model, executes it through a
read-only SQLite connection by default, and returns a concise answer.
"""

import argparse
import sqlite3
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE = "demo.sqlite"


def create_demo_database(database_path: str | Path) -> Path:
    """Create the repeatable demo e-commerce database and return its path."""

    path = Path(database_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE,
                country TEXT, created_at DATE DEFAULT CURRENT_DATE
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT,
                price REAL NOT NULL, stock INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id),
                product_id INTEGER REFERENCES products(id), quantity INTEGER NOT NULL,
                total REAL NOT NULL, order_date DATE DEFAULT CURRENT_DATE
            );
            INSERT OR IGNORE INTO customers VALUES
                (1, 'Alice Johnson', 'alice@example.com', 'USA', '2024-01-15'),
                (2, 'Bob Smith', 'bob@example.com', 'UK', '2024-02-20'),
                (3, 'Carlos Lima', 'carlos@example.com', 'Brazil', '2024-03-10'),
                (4, 'Diana Prince', 'diana@example.com', 'USA', '2024-01-05');
            INSERT OR IGNORE INTO products VALUES
                (1, 'Laptop Pro', 'Electronics', 1299.99, 45),
                (2, 'Wireless Mouse', 'Electronics', 29.99, 200),
                (3, 'Python Book', 'Books', 49.99, 120),
                (4, 'Standing Desk', 'Furniture', 599.99, 15);
            INSERT OR IGNORE INTO orders VALUES
                (1, 1, 1, 1, 1299.99, '2024-04-01'),
                (2, 1, 2, 2, 59.98, '2024-04-01'),
                (3, 2, 3, 1, 49.99, '2024-04-05'),
                (4, 3, 4, 1, 599.99, '2024-04-10'),
                (5, 4, 1, 1, 1299.99, '2024-04-12'),
                (6, 2, 2, 3, 89.97, '2024-04-15');
            """
        )
    return path


def validate_database_path(database_path: str | Path) -> Path:
    """Validate that a path points to an existing SQLite database file."""

    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}")
    if path.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
        raise ValueError("Database must use .sqlite, .sqlite3, or .db extension")
    return path


def sqlite_uri(database_path: str | Path, read_only: bool = True) -> str:
    """Build a SQLAlchemy SQLite URI with optional read-only mode."""

    path = validate_database_path(database_path)
    if read_only:
        return f"sqlite:///file:{quote(path.as_posix())}?mode=ro&uri=true"
    return f"sqlite:///{path.as_posix()}"


def build_agent(database_path: str | Path, read_only: bool = True):
    """Build the SQL agent and database wrapper for a SQLite file."""

    from langchain_community.agent_toolkits import SQLDatabaseToolkit
    from langchain_community.agent_toolkits.sql.base import create_sql_agent
    from langchain_community.utilities import SQLDatabase
    from langchain_openai import ChatOpenAI

    database = SQLDatabase.from_uri(sqlite_uri(database_path, read_only))
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    toolkit = SQLDatabaseToolkit(db=database, llm=model)
    agent = create_sql_agent(
        llm=model,
        toolkit=toolkit,
        agent_type="openai-tools",
        verbose=False,
    )
    return agent, database


def ask_database(agent, question: str) -> str:
    """Ask one natural-language question and return the model's answer."""

    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")
    return agent.invoke({"input": question})["output"]


def main() -> None:
    """Parse CLI arguments and run single-question or interactive mode."""

    parser = argparse.ArgumentParser(description="Natural-language SQLite query agent")
    parser.add_argument("--db", default=DEFAULT_DATABASE, help="SQLite database path")
    parser.add_argument("--question", help="Ask one question and exit")
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Allow write access; use only with a disposable database",
    )
    args = parser.parse_args()

    try:
        database_path = (
            create_demo_database(args.db)
            if args.db == DEFAULT_DATABASE and not Path(args.db).exists()
            else validate_database_path(args.db)
        )
        agent, database = build_agent(database_path, read_only=not args.allow_write)
    except (FileNotFoundError, ValueError, ImportError) as error:
        parser.error(str(error))

    print(f"\nConnected to: {database_path}")
    print(f"Mode: {'read-write' if args.allow_write else 'read-only'}")
    print(f"Tables: {', '.join(database.get_usable_table_names())}\n")

    if args.question:
        try:
            print(ask_database(agent, args.question))
        except Exception as error:
            parser.error(f"Query failed: {error}")
        return

    print("SQL agent ready. Type 'quit' to exit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            continue
        try:
            print(f"\nAgent: {ask_database(agent, question)}\n")
        except Exception as error:
            print(f"\nQuery failed: {error}\n")


if __name__ == "__main__":
    main()
