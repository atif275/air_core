# file_operations.py
import os
import shutil
from datetime import datetime
import re
import glob
from pathlib import Path
from langchain_core.tools import tool
import fnmatch

@tool
def get_current_directory() -> str:
    """Get the current working directory."""
    print("get_current_directory function called")
    return f"Current Directory: {os.getcwd()}"

@tool
def change_directory(new_dir: str) -> str:
    """Change current working directory."""
    print(f"change_directory function called with: {new_dir}")
    try:
        # Normalize path
        normalized_path = os.path.abspath(os.path.expanduser(new_dir))
        print(f"Normalized path: {normalized_path}")
        
        if not os.path.exists(normalized_path):
            return f"Error: Directory '{normalized_path}' does not exist."
        
        if not os.path.isdir(normalized_path):
            return f"Error: '{normalized_path}' is not a directory."
            
        os.chdir(normalized_path)
        return f"Changed to directory: {os.getcwd()}"
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied accessing directory '{normalized_path}'. {str(e)}"
    except Exception as e:
        print(f"Error changing directory: {str(e)}")
        return f"Error changing directory: {str(e)}"

@tool
def list_directories() -> str:
    """List all available directories."""
    print("list_directories function called")
    current_directory = os.getcwd()
    directories = []
    try:
        for item in os.listdir(current_directory):
            item_path = os.path.join(current_directory, item)
            if os.path.isdir(item_path):
                directories.append(f"- {item}/")
        return "Available Directories:\n" + "\n".join(directories)
    except Exception as e:
        print(f"Error listing directories: {str(e)}")
        return f"Error listing directories: {str(e)}"

@tool
def list_current_files() -> str:
    """List files in the current directory."""
    print("list_current_files function called")
    current_directory = os.getcwd()
    files_info = []
    try:
        for item in os.listdir(current_directory):
            item_path = os.path.join(current_directory, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                modified = datetime.fromtimestamp(os.path.getmtime(item_path))
                files_info.append(f"- {item} (Size: {size} bytes, Modified: {modified})")
        return "Files in current directory:\n" + "\n".join(files_info)
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied accessing directory. {str(e)}"
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        return f"Error listing files: {str(e)}"

@tool
def create_file(filename: str, content: str) -> str:
    """Create a new file with user content."""
    print(f"create_file function called with filename: {filename}")
    try:
        # Normalize path
        normalized_path = os.path.abspath(os.path.expanduser(filename))
        print(f"Normalized path: {normalized_path}")
        
        # Check if parent directory exists
        parent_dir = os.path.dirname(normalized_path)
        if parent_dir and not os.path.exists(parent_dir):
            return f"Error: Parent directory '{parent_dir}' does not exist."
        
        # Check permissions
        if parent_dir and not os.access(parent_dir, os.W_OK):
            return f"Error: Permission denied. You don't have write access to '{parent_dir}'."
            
        # Create file
        with open(normalized_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Verify file was created
        if not os.path.exists(normalized_path):
            return f"Error: Failed to create file '{normalized_path}'."
            
        print(f"Successfully created file: {normalized_path}")
        return f"File '{normalized_path}' created successfully."
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied creating file. {str(e)}"
    except Exception as e:
        print(f"Error creating file: {str(e)}")
        return f"Error creating file: {str(e)}"

@tool
def read_file(filename: str) -> str:
    """Read and display file content."""
    print(f"read_file function called with filename: {filename}")
    try:
        # Normalize path
        normalized_path = os.path.abspath(os.path.expanduser(filename))
        print(f"Normalized path: {normalized_path}")
        
        # Check if file exists
        if not os.path.exists(normalized_path):
            return f"Error: File '{normalized_path}' does not exist."
            
        # Check if path is a file
        if not os.path.isfile(normalized_path):
            return f"Error: '{normalized_path}' is not a file."
            
        # Check permissions
        if not os.access(normalized_path, os.R_OK):
            return f"Error: Permission denied. You don't have read access to '{normalized_path}'."
            
        # Get file size
        file_size = os.path.getsize(normalized_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return f"Error: File '{normalized_path}' is too large ({file_size} bytes) to read safely. Consider opening it with a more appropriate tool."
        
        # Read file content
        with open(normalized_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"Successfully read file: {normalized_path} ({len(content)} characters)")
        return f"Content of '{normalized_path}':\n{content}"
    except UnicodeDecodeError:
        print(f"Unicode decode error for: {normalized_path}")
        return f"Error: File '{normalized_path}' appears to be a binary file and cannot be displayed as text."
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied reading file. {str(e)}"
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return f"Error reading file: {str(e)}"

@tool
def update_file(filename: str, content: str) -> str:
    """Update existing file content."""
    print(f"update_file function called with filename: {filename}")
    try:
        # Normalize path
        normalized_path = os.path.abspath(os.path.expanduser(filename))
        print(f"Normalized path: {normalized_path}")
        
        # Check if file exists
        if not os.path.exists(normalized_path):
            return f"Error: File '{normalized_path}' does not exist."
            
        # Check if path is a file
        if not os.path.isfile(normalized_path):
            return f"Error: '{normalized_path}' is not a file."
            
        # Check permissions
        if not os.access(normalized_path, os.W_OK):
            return f"Error: Permission denied. You don't have write access to '{normalized_path}'."
        
        # Create backup
        try:
            backup_path = f"{normalized_path}.bak"
            shutil.copy2(normalized_path, backup_path)
            print(f"Created backup at: {backup_path}")
        except Exception as e:
            print(f"Warning: Could not create backup: {str(e)}")
        
        # Update file content
        with open(normalized_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Successfully updated file: {normalized_path}")
        return f"File '{normalized_path}' updated successfully."
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied updating file. {str(e)}"
    except Exception as e:
        print(f"Error updating file: {str(e)}")
        return f"Error updating file: {str(e)}"

@tool
def delete_file(filename: str) -> str:
    """Delete a file from any location on the computer."""
    print(f"delete_file function called with path: {filename}")
    try:
        # Normalize the path to handle any path format issues
        normalized_path = os.path.abspath(os.path.expanduser(filename))
        print(f"Normalized path: {normalized_path}")
        
        if os.path.exists(normalized_path):
            if not os.path.isfile(normalized_path):
                return f"Error: '{normalized_path}' exists but is not a file. It's a directory or special file."
                
            # Check if we have permission to delete
            if not os.access(os.path.dirname(normalized_path) or '.', os.W_OK):
                return f"Error: Permission denied. You don't have write access to delete '{normalized_path}'."
            
            # Print additional debug info
            print(f"File exists and is deletable: {normalized_path}")
            print(f"Parent directory: {os.path.dirname(normalized_path)}")
            
            # Try to delete the file
            os.remove(normalized_path)
            
            # Verify deletion was successful
            if os.path.exists(normalized_path):
                print(f"WARNING: File still exists after deletion attempt: {normalized_path}")
                return f"Error: Failed to delete '{normalized_path}'. File still exists after deletion attempt."
            
            print(f"Successfully deleted file: {normalized_path}")
            return f"File '{normalized_path}' deleted successfully."
        else:
            print(f"File not found: {normalized_path}")
            return f"File '{normalized_path}' does not exist."
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Permission error deleting file: {str(e)}"
    except IsADirectoryError:
        print(f"Path is a directory: {normalized_path}")
        return f"Error: '{normalized_path}' is a directory. Use remove_directory instead."
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        return f"Error deleting file: {str(e)}"

@tool
def create_directory(dirname: str) -> str:
    """Create a new directory."""
    print("create_directory function called")
    try:
        # Check if the directory is writable before attempting to create
        parent_dir = os.path.dirname(os.path.abspath(dirname)) if os.path.dirname(dirname) else os.getcwd()
        if not os.access(parent_dir, os.W_OK):
            return f"Permission denied: You don't have write access to '{parent_dir}'. Try creating directories in your current working directory instead: {os.getcwd()}"
        
        os.makedirs(dirname, exist_ok=True)
        return f"Directory '{dirname}' created successfully."
    except PermissionError:
        return f"Permission denied: Cannot create directory '{dirname}'. Try creating directories in your current working directory: {os.getcwd()}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"

@tool
def remove_directory(dirname: str) -> str:
    """Remove a directory."""
    print("remove_directory function called")
    try:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
            return f"Directory '{dirname}' removed successfully."
        return f"Directory '{dirname}' does not exist."
    except Exception as e:
        return f"Error removing directory: {str(e)}"

@tool
def rename_file(old_name: str, new_name: str) -> str:
    """Rename a file."""
    print(f"rename_file function called with: {old_name} -> {new_name}")
    try:
        # Normalize paths
        old_path = os.path.abspath(os.path.expanduser(old_name))
        print(f"Normalized old path: {old_path}")
        
        # For the new path, check if it's a full path or just a filename
        if os.path.dirname(new_name):
            # It's a full path
            new_path = os.path.abspath(os.path.expanduser(new_name))
        else:
            # It's just a filename, put it in the same directory as the old file
            new_path = os.path.join(os.path.dirname(old_path), new_name)
        
        print(f"Normalized new path: {new_path}")
        
        # Check if source exists
        if not os.path.exists(old_path):
            return f"Error: Source file '{old_path}' does not exist."
            
        # Check if source is a file
        if not os.path.isfile(old_path):
            return f"Error: '{old_path}' is not a file."
            
        # Check if destination already exists
        if os.path.exists(new_path):
            return f"Error: Destination file '{new_path}' already exists."
            
        # Check permissions
        if not os.access(os.path.dirname(old_path), os.W_OK):
            return f"Error: Permission denied. You don't have write access to the source directory."
            
        if os.path.dirname(old_path) != os.path.dirname(new_path) and not os.access(os.path.dirname(new_path), os.W_OK):
            return f"Error: Permission denied. You don't have write access to the destination directory."
        
        # Rename the file
        os.rename(old_path, new_path)
        
        # Verify the rename was successful
        if not os.path.exists(new_path):
            return f"Error: Failed to rename '{old_path}' to '{new_path}'."
            
        print(f"Successfully renamed: {old_path} -> {new_path}")
        return f"File renamed from '{old_path}' to '{new_path}' successfully."
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied renaming file. {str(e)}"
    except Exception as e:
        print(f"Error renaming file: {str(e)}")
        return f"Error renaming file: {str(e)}"

@tool
def get_file_info(filename: str) -> str:
    """Get detailed information about a file."""
    print(f"get_file_info function called with filename: {filename}")
    try:
        # Normalize path
        normalized_path = os.path.abspath(os.path.expanduser(filename))
        print(f"Normalized path: {normalized_path}")
        
        # Check if file exists
        if not os.path.exists(normalized_path):
            return f"Error: File '{normalized_path}' does not exist."
            
        # Check if path is a file
        if not os.path.isfile(normalized_path):
            return f"Error: '{normalized_path}' is not a file."
            
        # Check permissions
        if not os.access(normalized_path, os.R_OK):
            return f"Error: Permission denied. You don't have read access to '{normalized_path}'."
        
        # Get file info
        stats = os.stat(normalized_path)
        
        # Get file type
        file_type = "Unknown"
        if normalized_path.endswith(('.txt', '.md', '.csv')):
            file_type = "Text file"
        elif normalized_path.endswith(('.py', '.js', '.java', '.c', '.cpp')):
            file_type = "Source code"
        elif normalized_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            file_type = "Image file"
        elif normalized_path.endswith(('.mp3', '.wav', '.flac')):
            file_type = "Audio file"
        elif normalized_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            file_type = "Video file"
        elif normalized_path.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
            file_type = "Document file"
        
        # Build info string
        info = f"File Information for '{normalized_path}':\n"
        info += f"Type: {file_type}\n"
        info += f"Size: {stats.st_size} bytes ({stats.st_size/1024:.2f} KB)\n"
        info += f"Created: {datetime.fromtimestamp(stats.st_ctime)}\n"
        info += f"Last Modified: {datetime.fromtimestamp(stats.st_mtime)}\n"
        info += f"Last Accessed: {datetime.fromtimestamp(stats.st_atime)}\n"
        info += f"File Mode: {stats.st_mode}\n"
        info += f"Owner UID: {stats.st_uid}\n"
        
        print(f"Successfully got info for: {normalized_path}")
        return info
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        return f"Error: Permission denied accessing file. {str(e)}"
    except Exception as e:
        print(f"Error getting file info: {str(e)}")
        return f"Error getting file info: {str(e)}"

@tool
def find_files(pattern: str, directory: str = None, recursive: bool = True, search_all: bool = False) -> str:
    """
    Find files matching a pattern across directories.
    
    Args:
        pattern: The search pattern (supports * and ? wildcards)
        directory: The specific directory to search in (default: current directory, ignored if search_all=True)
        recursive: Whether to search recursively through subdirectories (default: True)
        search_all: If True, searches from multiple root directories (default: False)
    
    Returns:
        A string containing the paths of all matched files
    """
    print("find_files function called")
    try:
        matched_files = []
        
        if search_all:
            # Define common root directories to search based on platform
            import platform
            system = platform.system()
            
            search_roots = []
            if system == "Windows":
                # Windows drives
                import string
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
                search_roots.extend(drives)
                # Also add common user directories
                if 'USERPROFILE' in os.environ:
                    user_dir = os.environ['USERPROFILE']
                    search_roots.append(user_dir)
            elif system == "Darwin" or system == "Linux":  # macOS or Linux
                # Start from root but add common locations to optimize
                search_roots = ["/"]
                # Add home directory
                if 'HOME' in os.environ:
                    search_roots.append(os.environ['HOME'])
                # Add current directory
                search_roots.append(os.getcwd())
            
            # Search in each root directory
            for root in search_roots:
                try:
                    base_path = Path(root)
                    glob_pattern = f"**/{pattern}" if recursive else pattern
                    
                    # Use glob with timeout to avoid hanging
                    root_matches = [str(f) for f in base_path.glob(glob_pattern) if f.is_file()]
                    matched_files.extend(root_matches)
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    continue
        else:
            # Use specified directory or current directory
            search_dir = directory if directory else os.getcwd()
            base_path = Path(search_dir)
            
            # Check if the directory exists
            if not base_path.exists() or not base_path.is_dir():
                return f"Error: Directory '{search_dir}' does not exist or is not a directory."
            
            # Create glob pattern
            glob_pattern = f"**/{pattern}" if recursive else pattern
            
            # Find matching files
            matched_files = [str(f) for f in base_path.glob(glob_pattern) if f.is_file()]
        
        # Remove duplicates and sort results
        matched_files = sorted(set(matched_files))
        
        if matched_files:
            return f"Found {len(matched_files)} file(s):\n" + "\n".join(matched_files)
        else:
            search_location = "all accessible directories" if search_all else f"'{directory if directory else os.getcwd()}'"
            return f"No files matching '{pattern}' found in {search_location}."
    
    except Exception as e:
        return f"Error finding files: {str(e)}"
