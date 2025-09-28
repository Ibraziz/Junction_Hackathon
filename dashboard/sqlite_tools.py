import sqlite3
import json
from typing import List, Dict, Any, Optional
import pandas as pd

class SQLiteTools:
    """SQLite database tools for LLM function calling"""

    def __init__(self, db_path: str = "data/time_series.sqlite"):
        self.db_path = db_path

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a SQL query and return results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            column_names = [description[0] for description in cursor.description] if cursor.description else []

            # Fetch results
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                rows = cursor.fetchall()
                results = [dict(zip(column_names, row)) for row in rows]
                return {
                    "success": True,
                    "data": results,
                    "row_count": len(results),
                    "columns": column_names
                }
            else:
                # For INSERT, UPDATE, DELETE
                conn.commit()
                return {
                    "success": True,
                    "rows_affected": cursor.rowcount,
                    "last_insert_id": cursor.lastrowid if cursor.lastrowid else None
                }

        except sqlite3.Error as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        finally:
            if 'conn' in locals():
                conn.close()

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table"""
        query = f"PRAGMA table_info({table_name})"
        result = self.execute_query(query)

        if result["success"]:
            return {
                "success": True,
                "table_name": table_name,
                "columns": result["data"]
            }
        return result

    def list_tables(self) -> Dict[str, Any]:
        """List all tables in the database"""
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = self.execute_query(query)

        if result["success"]:
            return {
                "success": True,
                "tables": [table["name"] for table in result["data"]]
            }
        return result

    def get_table_data(self, table_name: str, limit: int = 100) -> Dict[str, Any]:
        """Get data from a table with optional limit"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.execute_query(query)

# Global instance
sqlite_tools = SQLiteTools()

def execute_sql_query(query: str, params: Optional[List[Any]] = None) -> str:
    """Execute SQL query - function for LLM tool calling"""
    result = sqlite_tools.execute_query(query, params)
    return json.dumps(result)

def get_table_schema(table_name: str) -> str:
    """Get table schema - function for LLM tool calling"""
    result = sqlite_tools.get_table_info(table_name)
    return json.dumps(result)

def list_database_tables() -> str:
    """List all tables - function for LLM tool calling"""
    result = sqlite_tools.list_tables()
    return json.dumps(result)

def get_table_data(table_name: str, limit: int = 100) -> str:
    """Get table data - function for LLM tool calling"""
    result = sqlite_tools.get_table_data(table_name, limit)
    return json.dumps(result)