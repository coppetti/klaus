#!/usr/bin/env python3
"""
Memory Backup & Restore
=======================
Backup and restore agent memory database.

Usage:
    # Create backup
    python scripts/backup-memory.py backup
    
    # List backups
    python scripts/backup-memory.py list
    
    # Restore from backup
    python scripts/backup-memory.py restore backup_20240222_123045
    
    # Auto-backup (use in cron)
    python scripts/backup-memory.py auto
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Colors
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✓ {msg}{Colors.END}")
def print_info(msg): print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")
def print_error(msg): print(f"{Colors.RED}✗ {msg}{Colors.END}")

def get_memory_path() -> Path:
    """Get memory database path from config or default."""
    config_path = Path("init.yaml")
    
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
            db_path = config.get('memory', {}).get('sqlite', {}).get('path', './memory.db')
            return Path(db_path)
        except:
            pass
    
    # Default locations to check
    defaults = [
        Path("memory/agent_memory.db"),
        Path("memory.db"),
        Path("workspace/memory.db"),
    ]
    
    for path in defaults:
        if path.exists():
            return path
    
    return defaults[0]  # Return first default if none exist

def get_backup_dir() -> Path:
    """Get backup directory."""
    backup_dir = Path("backups/memory")
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def create_backup(memory_path: Path, name: Optional[str] = None) -> Path:
    """Create a backup of the memory database."""
    if not memory_path.exists():
        print_error(f"Memory database not found: {memory_path}")
        sys.exit(1)
    
    backup_dir = get_backup_dir()
    
    # Generate backup name
    if name:
        backup_name = f"backup_{name}"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
    
    backup_path = backup_dir / backup_name
    
    # Copy database
    shutil.copy2(memory_path, backup_path)
    
    # Also backup as JSON for readability
    try:
        import sqlite3
        import json
        
        conn = sqlite3.connect(memory_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories")
        
        rows = []
        for row in cursor.fetchall():
            rows.append({
                "id": row[0],
                "content": row[1],
                "category": row[2],
                "importance": row[3],
                "metadata": row[4],
                "created_at": row[5],
                "access_count": row[6],
                "last_accessed": row[7]
            })
        
        conn.close()
        
        json_path = backup_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(rows, f, indent=2, default=str)
        
        print_success(f"Backup created: {backup_path}")
        print_info(f"JSON export: {json_path}")
        print_info(f"Total memories: {len(rows)}")
        
    except Exception as e:
        print_warning(f"Could not create JSON export: {e}")
        print_success(f"Database backup created: {backup_path}")
    
    return backup_path

def list_backups() -> List[Path]:
    """List all available backups."""
    backup_dir = get_backup_dir()
    
    if not backup_dir.exists():
        print_info("No backups directory found.")
        return []
    
    backups = sorted(backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        print_info("No backups found.")
        return []
    
    print("\nAvailable backups:")
    print("-" * 80)
    print(f"{'Name':<40} {'Date':<20} {'Size':<15}")
    print("-" * 80)
    
    for backup in backups:
        if backup.suffix == '.json':
            continue
        
        stat = backup.stat()
        date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        size = f"{stat.st_size / 1024:.1f} KB"
        print(f"{backup.name:<40} {date:<20} {size:<15}")
    
    print("-" * 80)
    print(f"Total: {len([b for b in backups if b.suffix != '.json'])}")
    
    return backups

def restore_backup(backup_name: str, memory_path: Path):
    """Restore memory from backup."""
    backup_dir = get_backup_dir()
    
    # Find backup
    backup_path = backup_dir / backup_name
    if not backup_path.exists():
        # Try with backup_ prefix
        backup_path = backup_dir / f"backup_{backup_name}"
    
    if not backup_path.exists():
        print_error(f"Backup not found: {backup_name}")
        print_info("Use 'list' command to see available backups.")
        sys.exit(1)
    
    # Confirm
    print_warning(f"This will REPLACE your current memory database!")
    print_info(f"Backup: {backup_path}")
    print_info(f"Target: {memory_path}")
    
    confirm = input("\nAre you sure? [y/N]: ").strip().lower()
    if confirm != 'y':
        print_info("Restore cancelled.")
        return
    
    # Create safety backup of current
    if memory_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_path = backup_dir / f"safety_before_restore_{timestamp}"
        shutil.copy2(memory_path, safety_path)
        print_info(f"Safety backup created: {safety_path.name}")
    
    # Restore
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, memory_path)
    
    print_success(f"Memory restored from: {backup_path.name}")

def auto_backup(memory_path: Path):
    """Create backup with auto-naming and cleanup."""
    backup_path = create_backup(memory_path)
    
    # Cleanup old backups (keep last 10)
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Keep only .db files, remove old ones
    db_backups = [b for b in backups if b.suffix == '.db' or not b.suffix]
    if len(db_backups) > 10:
        for old_backup in db_backups[10:]:
            old_backup.unlink()
            # Also remove JSON if exists
            json_file = old_backup.with_suffix('.json')
            if json_file.exists():
                json_file.unlink()
            print_info(f"Cleaned up old backup: {old_backup.name}")
    
    return backup_path

def export_to_json(memory_path: Path, output_path: Path):
    """Export memory to JSON format."""
    import sqlite3
    import json
    
    if not memory_path.exists():
        print_error(f"Memory database not found: {memory_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(memory_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories ORDER BY created_at DESC")
    
    rows = []
    for row in cursor.fetchall():
        rows.append({
            "id": row[0],
            "content": row[1],
            "category": row[2],
            "importance": row[3],
            "metadata": row[4],
            "created_at": row[5],
            "access_count": row[6],
            "last_accessed": row[7]
        })
    
    conn.close()
    
    with open(output_path, 'w') as f:
        json.dump(rows, f, indent=2, default=str)
    
    print_success(f"Exported {len(rows)} memories to: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Backup and restore agent memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/backup-memory.py backup              # Create timestamped backup
  python scripts/backup-memory.py backup my-name      # Create named backup
  python scripts/backup-memory.py list                # List all backups
  python scripts/backup-memory.py restore backup_20240222_123045  # Restore
  python scripts/backup-memory.py auto                # Auto-backup with cleanup
  python scripts/backup-memory.py export memories.json  # Export to JSON
        """
    )
    
    parser.add_argument(
        "command",
        choices=["backup", "list", "restore", "auto", "export"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "name",
        nargs="?",
        help="Backup name (for backup/restore/export commands)"
    )
    
    parser.add_argument(
        "--memory-path",
        help="Path to memory database (auto-detected if not specified)"
    )
    
    args = parser.parse_args()
    
    # Get memory path
    memory_path = Path(args.memory_path) if args.memory_path else get_memory_path()
    
    if args.command == "backup":
        create_backup(memory_path, args.name)
    
    elif args.command == "list":
        list_backups()
    
    elif args.command == "restore":
        if not args.name:
            print_error("Please specify backup name to restore")
            print_info("Use: python scripts/backup-memory.py restore <backup_name>")
            sys.exit(1)
        restore_backup(args.name, memory_path)
    
    elif args.command == "auto":
        auto_backup(memory_path)
    
    elif args.command == "export":
        output = args.name or "memory_export.json"
        export_to_json(memory_path, Path(output))

if __name__ == "__main__":
    main()
