"""Utilities for operating system interactions, compatible with both Windows and Unix."""
import os
import platform
import shutil
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_disk_usage(path: str) -> Dict[str, Any]:
    """
    Get disk usage statistics for the given path in a platform-independent way.
    
    Args:
        path: Path to check disk usage for
        
    Returns:
        Dictionary with disk usage statistics
    """
    try:
        if platform.system() == "Windows":
            # Windows implementation uses shutil
            total, used, free = shutil.disk_usage(path)
            return {
                "total_mb": total / (1024 * 1024),
                "used_mb": used / (1024 * 1024),
                "free_mb": free / (1024 * 1024),
                "usage_percent": (used / total) * 100 if total > 0 else 0
            }
        else:
            # Unix implementation uses os.statvfs
            disk_stats = os.statvfs(path)
            total_space = disk_stats.f_blocks * disk_stats.f_frsize
            free_space = disk_stats.f_bfree * disk_stats.f_frsize
            used_space = total_space - free_space
            
            return {
                "total_mb": total_space / (1024 * 1024),
                "used_mb": used_space / (1024 * 1024),
                "free_mb": free_space / (1024 * 1024),
                "usage_percent": (used_space / total_space) * 100 if total_space > 0 else 0
            }
    except Exception as e:
        logger.error(f"Error getting disk usage for {path}: {str(e)}")
        return {
            "total_mb": 0,
            "used_mb": 0,
            "free_mb": 0,
            "usage_percent": 0,
            "error": str(e)
        }

def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
        
    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {str(e)}")
        return False
