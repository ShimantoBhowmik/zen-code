"""
File system utilities for the Backspace CLI
"""

import os
import shutil
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path

def safe_file_read(file_path: str, max_size_mb: int = 10) -> str:
    """Safely read a file with size limits"""
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            raise Exception(f"File too large: {file_size} bytes (limit: {max_size_bytes})")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except UnicodeDecodeError:
        try:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception:
            return f"[Binary file - {file_size} bytes]"
    except Exception as e:
        return f"[Error reading file: {str(e)}]"

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get detailed information about a file"""
    try:
        path = Path(file_path)
        stat = path.stat()
        
        return {
            "exists": True,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "extension": path.suffix,
            "name": path.name,
            "parent": str(path.parent),
            "absolute_path": str(path.absolute())
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }

def create_backup(file_path: str, backup_dir: Optional[str] = None) -> str:
    """Create a backup of a file"""
    try:
        if not os.path.exists(file_path):
            raise Exception(f"File does not exist: {file_path}")
        
        if backup_dir is None:
            backup_dir = os.path.dirname(file_path)
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        base_name = os.path.basename(file_path)
        backup_name = f"{base_name}.backup"
        backup_path = os.path.join(backup_dir, backup_name)
        
        # If backup already exists, add timestamp
        if os.path.exists(backup_path):
            import time
            timestamp = int(time.time())
            backup_name = f"{base_name}.backup.{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        return backup_path
        
    except Exception as e:
        raise Exception(f"Failed to create backup: {str(e)}")

def get_directory_size(path: str) -> Dict[str, Any]:
    """Get the total size of a directory"""
    try:
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for dirpath, dirnames, filenames in os.walk(path):
            dir_count += len(dirnames)
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    # Skip files that can't be accessed
                    pass
        
        return {
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "dir_count": dir_count
        }
        
    except Exception as e:
        return {"error": str(e)}

def find_files_by_extension(directory: str, extensions: List[str], max_depth: int = 10) -> List[str]:
    """Find files by extension in a directory"""
    found_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            # Limit depth
            depth = root[len(directory):].count(os.sep)
            if depth >= max_depth:
                dirs[:] = []  # Don't go deeper
                continue
            
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in [ext.lower() for ext in extensions]:
                    found_files.append(os.path.join(root, file))
        
        return found_files
        
    except Exception as e:
        print(f"Error finding files: {str(e)}")
        return []

def create_temp_directory(prefix: str = "backspace_") -> str:
    """Create a temporary directory"""
    return tempfile.mkdtemp(prefix=prefix)

def cleanup_directory(directory: str, force: bool = False):
    """Safely cleanup a directory"""
    try:
        if not os.path.exists(directory):
            return f"Directory does not exist: {directory}"
        
        if not force:
            # Ask for confirmation for important directories
            important_dirs = ['/usr', '/bin', '/etc', '/var', '/home']
            if any(directory.startswith(d) for d in important_dirs):
                raise Exception(f"Refusing to delete important directory: {directory}")
        
        shutil.rmtree(directory)
        return f"Successfully deleted: {directory}"
        
    except Exception as e:
        return f"Failed to delete directory: {str(e)}"

def ensure_directory_exists(directory: str) -> str:
    """Ensure a directory exists, create if needed"""
    try:
        os.makedirs(directory, exist_ok=True)
        return f"Directory ready: {directory}"
    except Exception as e:
        raise Exception(f"Failed to create directory: {str(e)}")

def get_common_file_types(directory: str) -> Dict[str, List[str]]:
    """Categorize files by common types"""
    categories = {
        "source_code": ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs'],
        "web": ['.html', '.css', '.scss', '.sass', '.less'],
        "config": ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'],
        "documentation": ['.md', '.txt', '.rst', '.tex'],
        "images": ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'],
        "data": ['.csv', '.json', '.xml', '.sql', '.db', '.sqlite'],
        "build": ['.sh', '.bat', '.ps1', 'Dockerfile', 'Makefile'],
        "other": []
    }
    
    result = {category: [] for category in categories.keys()}
    
    try:
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                categorized = False
                for category, extensions in categories.items():
                    if category == "other":
                        continue
                    if file_ext in extensions or file in extensions:
                        result[category].append(file_path)
                        categorized = True
                        break
                
                if not categorized:
                    result["other"].append(file_path)
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

def is_text_file(file_path: str) -> bool:
    """Check if a file is likely a text file"""
    try:
        # Check file extension first
        text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.scss', '.json', 
            '.yaml', '.yml', '.xml', '.csv', '.sql', '.sh', '.bat', '.ps1', 
            '.c', '.cpp', '.h', '.java', '.cs', '.php', '.rb', '.go', '.rs',
            '.jsx', '.tsx', '.vue', '.svelte', '.toml', '.ini', '.cfg', '.conf'
        }
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext in text_extensions:
            return True
        
        # Try to read first few bytes
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            
        # Check for null bytes (common in binary files)
        if b'\\x00' in chunk:
            return False
        
        # Try to decode as UTF-8
        try:
            chunk.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False
            
    except Exception:
        return False
