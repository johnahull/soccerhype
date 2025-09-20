#!/usr/bin/env python3
"""
Error Handling and Logging Utilities
Provides comprehensive error handling, user-friendly error messages,
and detailed logging for troubleshooting.
"""

import logging
import pathlib
import sys
import traceback
import functools
from typing import Optional, Callable, Any, Dict
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

class SoccerHypeLogger:
    """Centralized logging system for SoccerHype"""

    def __init__(self, log_dir: Optional[pathlib.Path] = None):
        self.log_dir = log_dir or (pathlib.Path.cwd() / "logs")
        self.log_dir.mkdir(exist_ok=True)

        # Setup logging configuration
        self.setup_logging()

    def setup_logging(self):
        """Configure logging system"""
        log_file = self.log_dir / f"soccerhype_{datetime.now().strftime('%Y%m%d')}.log"

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)

        # Root logger
        root_logger = logging.getLogger('soccerhype')
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance"""
        return logging.getLogger(f'soccerhype.{name}')

# Global logger instance
logger_instance = SoccerHypeLogger()

class ErrorCategories:
    """Categorizes different types of errors with user-friendly messages"""

    FILE_NOT_FOUND = "file_not_found"
    VIDEO_PROCESSING = "video_processing"
    FFMPEG_ERROR = "ffmpeg_error"
    PERMISSION_ERROR = "permission_error"
    DISK_SPACE = "disk_space"
    CODEC_ERROR = "codec_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"

    ERROR_MESSAGES = {
        FILE_NOT_FOUND: {
            "title": "File Not Found",
            "message": "The required file could not be found. Please check that the file exists and try again.",
            "suggestions": [
                "Verify the file path is correct",
                "Check if the file was moved or deleted",
                "Ensure you have permission to access the file location"
            ]
        },
        VIDEO_PROCESSING: {
            "title": "Video Processing Error",
            "message": "An error occurred while processing the video file.",
            "suggestions": [
                "Check if the video file is corrupted",
                "Try converting the video to a supported format (MP4, MOV, AVI)",
                "Ensure the video file is not in use by another application"
            ]
        },
        FFMPEG_ERROR: {
            "title": "FFmpeg Error",
            "message": "FFmpeg encountered an error while processing the video.",
            "suggestions": [
                "Verify FFmpeg is properly installed",
                "Check if the video codec is supported",
                "Try with a different video file to isolate the issue",
                "Update FFmpeg to the latest version"
            ]
        },
        PERMISSION_ERROR: {
            "title": "Permission Denied",
            "message": "Access to the file or directory was denied.",
            "suggestions": [
                "Check file and directory permissions",
                "Run the application with appropriate privileges",
                "Ensure the disk is not write-protected"
            ]
        },
        DISK_SPACE: {
            "title": "Insufficient Disk Space",
            "message": "There is not enough disk space to complete the operation.",
            "suggestions": [
                "Free up disk space by deleting unnecessary files",
                "Move files to a different drive with more space",
                "Clean up temporary files and caches"
            ]
        },
        CODEC_ERROR: {
            "title": "Video Codec Error",
            "message": "The video codec is not supported or there's an encoding issue.",
            "suggestions": [
                "Convert the video to a widely supported format (H.264 MP4)",
                "Install additional codec packages",
                "Try opening the video in a different player to verify it's valid"
            ]
        },
        NETWORK_ERROR: {
            "title": "Network Error",
            "message": "A network-related error occurred.",
            "suggestions": [
                "Check your internet connection",
                "Verify firewall settings",
                "Try again after a few moments"
            ]
        },
        VALIDATION_ERROR: {
            "title": "Invalid Input",
            "message": "The provided input is invalid or incomplete.",
            "suggestions": [
                "Check that all required fields are filled",
                "Verify the format of entered data",
                "Follow the specified input guidelines"
            ]
        },
        UNKNOWN_ERROR: {
            "title": "Unexpected Error",
            "message": "An unexpected error occurred.",
            "suggestions": [
                "Check the log files for more details",
                "Try restarting the application",
                "Report this issue if it persists"
            ]
        }
    }

class ErrorHandler:
    """Handles errors with appropriate user feedback and logging"""

    def __init__(self, logger_name: str = "error_handler"):
        self.logger = logger_instance.get_logger(logger_name)

    def categorize_error(self, error: Exception) -> str:
        """Categorize an error based on its type and message"""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # File-related errors
        if isinstance(error, FileNotFoundError):
            return ErrorCategories.FILE_NOT_FOUND
        elif isinstance(error, PermissionError):
            return ErrorCategories.PERMISSION_ERROR

        # FFmpeg-related errors
        if "ffmpeg" in error_message or "codec" in error_message:
            if "codec" in error_message or "format" in error_message:
                return ErrorCategories.CODEC_ERROR
            return ErrorCategories.FFMPEG_ERROR

        # Disk space errors
        if "no space" in error_message or "disk full" in error_message:
            return ErrorCategories.DISK_SPACE

        # Network errors
        if "network" in error_message or "connection" in error_message:
            return ErrorCategories.NETWORK_ERROR

        # Video processing errors
        if "video" in error_message or "opencv" in error_message:
            return ErrorCategories.VIDEO_PROCESSING

        # Validation errors
        if isinstance(error, ValueError) or "invalid" in error_message:
            return ErrorCategories.VALIDATION_ERROR

        return ErrorCategories.UNKNOWN_ERROR

    def handle_error(self, error: Exception, context: str = "",
                    show_dialog: bool = True, parent_window: Optional[tk.Widget] = None) -> None:
        """Handle an error with appropriate logging and user feedback"""
        # Log the full error details
        self.logger.error(f"Error in {context}: {type(error).__name__}: {error}")
        self.logger.debug(f"Full traceback:\n{traceback.format_exc()}")

        # Categorize and get user-friendly message
        category = self.categorize_error(error)
        error_info = ErrorCategories.ERROR_MESSAGES[category]

        if show_dialog:
            self.show_error_dialog(error_info, str(error), context, parent_window)

    def show_error_dialog(self, error_info: Dict, technical_details: str,
                         context: str, parent_window: Optional[tk.Widget] = None):
        """Show a user-friendly error dialog"""
        try:
            # Create detailed message
            message = error_info["message"]
            if context:
                message += f"\n\nContext: {context}"

            message += "\n\nSuggestions:"
            for suggestion in error_info["suggestions"]:
                message += f"\n• {suggestion}"

            message += f"\n\nTechnical details: {technical_details}"

            # Show dialog
            if parent_window:
                messagebox.showerror(error_info["title"], message, parent=parent_window)
            else:
                messagebox.showerror(error_info["title"], message)

        except Exception as dialog_error:
            # Fallback to console if dialog fails
            self.logger.error(f"Failed to show error dialog: {dialog_error}")
            print(f"ERROR: {error_info['title']}: {error_info['message']}")

    def log_operation_start(self, operation: str, details: Dict[str, Any] = None):
        """Log the start of an operation"""
        message = f"Starting operation: {operation}"
        if details:
            message += f" with details: {details}"
        self.logger.info(message)

    def log_operation_success(self, operation: str, result: Any = None):
        """Log successful completion of an operation"""
        message = f"Operation completed successfully: {operation}"
        if result:
            message += f" with result: {result}"
        self.logger.info(message)

    def log_operation_warning(self, operation: str, warning: str):
        """Log a warning during an operation"""
        self.logger.warning(f"Warning in {operation}: {warning}")

def error_handler(context: str = "", show_dialog: bool = True,
                 logger_name: str = "decorator", reraise: bool = False):
    """Decorator for automatic error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(logger_name)
            operation_context = context or f"{func.__module__}.{func.__name__}"

            try:
                handler.log_operation_start(operation_context, {
                    "args": str(args)[:200],  # Limit log length
                    "kwargs": str(kwargs)[:200]
                })

                result = func(*args, **kwargs)

                handler.log_operation_success(operation_context)
                return result

            except Exception as e:
                handler.handle_error(e, operation_context, show_dialog)
                if reraise:
                    raise
                return None

        return wrapper
    return decorator

class ProgressReporter:
    """Reports progress of long-running operations with error handling"""

    def __init__(self, total_steps: int, operation_name: str = "Operation"):
        self.total_steps = total_steps
        self.current_step = 0
        self.operation_name = operation_name
        self.logger = logger_instance.get_logger("progress")
        self.start_time = datetime.now()

    def update(self, step_name: str = "", increment: int = 1) -> bool:
        """Update progress and return True if operation should continue"""
        try:
            self.current_step += increment
            progress_percent = (self.current_step / self.total_steps) * 100

            # Log progress
            if step_name:
                self.logger.info(f"{self.operation_name}: {step_name} ({progress_percent:.1f}%)")
            else:
                self.logger.info(f"{self.operation_name}: {progress_percent:.1f}% complete")

            return True

        except Exception as e:
            self.logger.error(f"Error updating progress: {e}")
            return False

    def complete(self):
        """Mark operation as complete"""
        elapsed = datetime.now() - self.start_time
        self.logger.info(f"{self.operation_name} completed in {elapsed.total_seconds():.2f} seconds")

class ValidationHelper:
    """Provides input validation with helpful error messages"""

    @staticmethod
    @error_handler("Input validation", show_dialog=False)
    def validate_file_path(path: pathlib.Path, extensions: list = None) -> bool:
        """Validate that a file path exists and has correct extension"""
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        if extensions and path.suffix.lower() not in extensions:
            raise ValueError(f"File must have one of these extensions: {extensions}")

        return True

    @staticmethod
    @error_handler("Directory validation", show_dialog=False)
    def validate_directory(path: pathlib.Path, create_if_missing: bool = False) -> bool:
        """Validate that a directory exists or can be created"""
        if not path.exists():
            if create_if_missing:
                path.mkdir(parents=True, exist_ok=True)
            else:
                raise FileNotFoundError(f"Directory does not exist: {path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        return True

    @staticmethod
    @error_handler("Disk space validation", show_dialog=False)
    def validate_disk_space(path: pathlib.Path, required_bytes: int) -> bool:
        """Validate that there's enough disk space"""
        try:
            import shutil
            free_bytes = shutil.disk_usage(path).free

            if free_bytes < required_bytes:
                required_mb = required_bytes / (1024 * 1024)
                free_mb = free_bytes / (1024 * 1024)
                raise OSError(f"Insufficient disk space. Required: {required_mb:.1f}MB, Available: {free_mb:.1f}MB")

            return True

        except Exception as e:
            raise OSError(f"Could not check disk space: {e}")

# Example usage functions
def safe_file_operation(operation_func: Callable, *args, **kwargs):
    """Safely execute a file operation with error handling"""
    handler = ErrorHandler("file_operations")
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        handler.handle_error(e, f"File operation: {operation_func.__name__}")
        return None

def get_system_info() -> Dict[str, str]:
    """Get system information for debugging"""
    import platform
    import subprocess

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "working_directory": str(pathlib.Path.cwd()),
    }

    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"],
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["ffmpeg"] = "Available"
        else:
            info["ffmpeg"] = "Not working"
    except Exception:
        info["ffmpeg"] = "Not found"

    # Check OpenCV
    try:
        import cv2
        info["opencv"] = cv2.__version__
    except ImportError:
        info["opencv"] = "Not installed"

    return info

# Initialize error handling system
def initialize_error_handling(log_dir: Optional[pathlib.Path] = None):
    """Initialize the error handling system"""
    global logger_instance
    logger_instance = SoccerHypeLogger(log_dir)

    # Log system info
    logger = logger_instance.get_logger("init")
    logger.info("SoccerHype error handling system initialized")

    system_info = get_system_info()
    for key, value in system_info.items():
        logger.info(f"System info - {key}: {value}")

if __name__ == "__main__":
    # Test the error handling system
    initialize_error_handling()

    # Test different error types
    handler = ErrorHandler("test")

    print("Testing error handling system...")

    # Test file not found
    try:
        raise FileNotFoundError("Test file not found")
    except Exception as e:
        handler.handle_error(e, "Test file operation", show_dialog=False)

    # Test validation
    try:
        ValidationHelper.validate_file_path(pathlib.Path("nonexistent.txt"))
    except Exception as e:
        handler.handle_error(e, "Test validation", show_dialog=False)

    print("Error handling test completed. Check logs for details.")