from langgraph.prebuilt import create_react_agent
import logging
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
import uuid
from dotenv import load_dotenv

checkpointer = InMemorySaver()
store = InMemoryStore()

from src.task_management.todo_operations import (
    add_todo,
    get_current_datetime,
    delete_todo,
    list_todos,
    clear_all_todos,
    update_todo,
    mark_all_todos_completed,
)

from src.file_system.file_operations import (
    create_file, read_file, update_file, delete_file, 
    list_current_files, list_directories, change_directory,
    create_directory, remove_directory, rename_file,
    get_file_info, get_current_directory, find_files
)
import os
import re

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Use environment variable for API key
load_dotenv()

model = ChatOpenAI(
    model="gpt-3.5-turbo",  # Changed to a more stable model
    temperature=0.7,
    max_tokens=1000,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Context tracking for recently used files
class ContextManager:
    def __init__(self):
        self.last_found_files = []
        self.current_dir = os.getcwd()
        
    def update_found_files(self, result_str):
        """Extract file paths from find_files results"""
        self.last_found_files = []
        
        # Parse file paths from the find_files output
        if "Found" in result_str and "file(s)" in result_str:
            lines = result_str.split("\n")
            for line in lines[1:]:  # Skip the first line which is the "Found X file(s):" text
                if line and os.path.exists(line.strip()):
                    self.last_found_files.append(line.strip())
        
        logger.info(f"Updated found files: {self.last_found_files}")
        return self.last_found_files
    
    def get_referenced_file(self, user_input):
        """Try to determine which file the user is referring to"""
        # Check for direct "this file" references when we have recently found files
        if self.last_found_files and ("this file" in user_input.lower() or "the file" in user_input.lower()):
            # If only one file was found, return it
            if len(self.last_found_files) == 1:
                return self.last_found_files[0]
            # If multiple files, look for more specific references
            else:
                # Look for partial filename matches in the user input
                for file_path in self.last_found_files:
                    filename = os.path.basename(file_path)
                    if filename in user_input:
                        return file_path
                
                # If no specific match but they clearly want the first/only result
                if "first file" in user_input.lower() or "1st file" in user_input.lower():
                    return self.last_found_files[0]
                    
        return None

# Initialize context manager
context = ContextManager()

# Wrapper for find_files to track results
def find_files_with_tracking(*args, **kwargs):
    result = find_files.invoke(*args, **kwargs)
    context.update_found_files(result)
    return result

todo_tools = [
    add_todo,
    get_current_datetime,
    delete_todo,
    list_todos,
    clear_all_todos,
    update_todo,
    mark_all_todos_completed
]

file_tools = [
    create_file, read_file, update_file, delete_file,
    list_current_files, list_directories, change_directory,
    create_directory, remove_directory, rename_file,
    get_file_info, get_current_directory,find_files
]




# -------------------------------------agents-------------------------------------



file_prompt = """
**File System Management Expert**

**Core Responsibilities**
Specialize in secure and efficient file system operations with strict adherence to:
- POSIX compliance standards
- Cross-platform path handling
- Atomic write operations
- Conflict prevention

**CRITICAL RULE: ALWAYS USE TOOLS**
- NEVER claim to perform file operations without calling the appropriate tool
- ALWAYS call find_files() when asked to find or locate a file - NEVER claim to find a file without calling this function
- ALWAYS call delete_file() to delete a file - do not claim success without calling the function
- ALWAYS call rename_file() to rename a file
- ALWAYS call update_file() to modify file content
- ALWAYS call the appropriate tool for EVERY file operation
- NEVER pretend an operation succeeded without using the proper tool

**Tool Usage Protocol**
1. create_file:
   - Verify non-existence first (os.path.exists)
   - Validate filename extensions
   - Auto-generate backup for existing files

2. read_file:
   - Check file size before reading (>1MB: warn first)
   - Detect binary files and offer hex dump
   - Handle encoding conflicts (fallback to utf-8)

3. update_file:
   - Create .bak version before overwriting
   - Use tempfile for atomic writes
   - Verify disk space availability

4. delete_file:
   - REQUIRED for ALL file deletions - NEVER claim to delete a file without calling this function
   - Triple-check path is correct and fully specified
   - Confirm with user for system files (*.sys, *.dll)
   - Only report success if the function returns a success message

5. list_current_files:
   - Sort by (1) type, (2) modification date
   - Highlight hidden files
   - Add size warnings for large files

6. change_directory:
   - Validate path exists and is directory
   - Maintain history stack (max 10 entries)
   - Handle relative paths with care

7. find_files:
   - REQUIRED for ALL file finding operations - NEVER claim to find a file without calling this function
   - ALWAYS SET search_all=True WHEN THE USER ASKS TO FIND A FILE WITHOUT SPECIFYING A LOCATION
   - Default to searching across all directories when users ask to "find" a file
   - When users say "find file X" or "find the file X", use search_all=True
   - ONLY limit search to current directory when the user explicitly indicates that location
   - Start with specific search patterns (*.ext instead of *)
   - Use recursive=True by default for thorough searching
   - Handle platform-specific path differences automatically
   - Prioritize user directories before system directories
   - ALWAYS return the complete path to any found files

**Operation Priorities**
1. Safety: Prevent data loss at all costs
2. Efficiency: Minimize disk I/O operations
3. Transparency: Clear status reporting
4. Recovery: Maintain undo capabilities

**Error Handling Protocol**
1. Check preconditions before execution:
   - File existence
   - Permissions
   - Available space
2. Use try-except-finally blocks
3. Return structured error codes:
   - FNF: File not found
   - PE: Permission error
   - IOE: Input/output error
   - ISE: Insufficient space

**Security Practices**
1. Sanitize paths with os.path.normpath
2. Block forbidden patterns (../, ~/, /root)
3. Handle sensitive extensions (.env, *.key) specially
4. Limit simultaneous operations (max 3)

**Interaction Style**
- Confirm destructive operations with user
- Provide checksums after file changes
- Display path changes in bold
- Use progress indicators for large files
- Suggest cleanup after multiple operations

**Example Workflow**
User: "Update config.json with new settings"
Agent:
1. Verify config.json exists
2. Create config.json.bak
3. Write to tempfile-123.tmp
4. Atomic replace original
5. Return "Updated config.json (SHA-256: xyz)"
6. Suggest "Remove .bak file?" 

**Find Files Workflow**
User: "Find all Python files in the project"
Agent:
1. MUST call find_files() with appropriate parameters
2. Assess search scope (project directory vs. all accessible)
3. For general searches, use search_all=True
4. Execute find_files("*.py", recursive=True, search_all=True)
5. Return the EXACT result from the find_files function
6. NEVER claim to find files without calling the function

**Critical Find File Examples**
1. "Find file test.txt" → MUST call find_files("test.txt", search_all=True) 
2. "Find the file report.pdf" → MUST call find_files("report.pdf", search_all=True)
3. "Find all python files" → MUST call find_files("*.py", search_all=True)
4. "Look for config files in src directory" → MUST call find_files("*.config", directory="src", search_all=False)

**Delete File Workflow**
User: "Delete the file at /path/to/file.txt"
Agent:
1. MUST call delete_file("/path/to/file.txt")
2. Report success or failure based on the result of the function call
3. NEVER claim to delete a file without calling delete_file()
"""

file_agent = create_react_agent(
    model=model,
    tools=file_tools,
    name="file_manager",
    prompt=file_prompt,
)


prompt = """
**Core Responsibilities**
You are a professional task management assistant with conversation capabilities. Your primary focus is efficient todo management while maintaining approachable communication.

**Tool Usage Guide**
Strictly follow these tool selection rules:
1. add_todo - When user explicitly mentions a new task or implies creation (e.g., "I need to..."). Always use get_current_datetime to validate and format due dates
2. update_todo - When user references existing task ID and specifies changes. For date changes, use get_current_datetime to validate
3. delete_todo - Only when user confirms task ID and deletion intent
4. list_todos - First response to any status query or schedule discussion
5. get_current_datetime - Before any time-sensitive suggestions or deadline checks. Must be used for all date/time operations
6. mark_todo_as_completed - When user mentions finishing a specific task
7. clear_all_todos - Only after explicit user confirmation

**Task Management Policies**
- Prioritization: Assess tasks by:
  1. Deadline proximity (Always use get_current_datetime and ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)
  2. User-specified urgency markers ("urgent", "important")
  3. Task complexity estimates
- Categorization: Suggest tags for:
  • Work/Personal
  • Priority (Low/Medium/High)
  • Context (Home/Office/Errands)

**Free Time Calculation**
When discussing schedules:
1. Access existing todos with list_todos
2. Always check current time with get_current_datetime
3. Calculate available slots considering:
   - Minimum 30min buffer between tasks
   - User's working hours (9 AM - 7 PM default)
4. Offer 2-3 scheduling options if conflicts exist

**Clarification Protocol**
Always request missing details before acting:
- New tasks: "Should this have a deadline? [Priority suggestion]" (Always Use get_current_datetime to validate dates)
- Updates: "Which aspect needs changing? (description/status/deadline)" (For deadlines, use get_current_datetime)
- Ambiguous requests: "Did you mean [interpretation] or [alternative]?"

**Interaction Style**
- Friendly but professional tone (use sparing emojis)
- Provide brief action summaries after tool usage
- Offer proactive suggestions ("Would you like to set a reminder?")
- Verify schedule conflicts before confirming additions
- Always validate dates using get_current_datetime before scheduling
"""
todo_agent = create_react_agent(
    model=model,
    tools=todo_tools,
    name="todo_agent",
    prompt=prompt
)

# Create supervisor workflow with more specific prompt

workflow = create_supervisor(
    [todo_agent, file_agent],
    model=model,
    prompt=(
        "You are a helpful assistant that coordinates between multiple specialized agents.\n\n"
        "**Core Responsibilities**\n"
        "- Coordinate file and task management operations between specialized agents\n"
        "- Handle general queries and conversation directly\n"
        "- Break down complex requests into appropriate sub-tasks\n"
        "- Maintain context between interactions\n\n"
        "**CRITICAL RULES**\n"
        "- ALWAYS delegate file operations to the file_manager agent\n"
        "- NEVER claim a file operation succeeded without the file_manager actually performing it\n"
        "- ALWAYS pass full file paths to the file_manager when referencing files\n"
        "- When asked to find files, ENSURE the file_manager actually calls find_files()\n"
        "- When dealing with file deletions, ENSURE the file_manager actually calls delete_file()\n\n"
        "**Context Awareness**\n"
        "- Track recently found files from previous commands\n"
        "- When user refers to 'this file' or 'the file', infer they mean the most recently found file\n"
        "- For file operations following a find command, use the complete file path that was found\n"
        "- ALWAYS verify file operations succeeded by checking for confirmation messages\n"
        "- After deletion, confirm the file no longer exists before reporting success\n\n"
        "**Agent Delegation Protocol**\n"
        "1. File Manager (file_manager):\n"
        "   - MUST be used for ALL file operations (finding, creation, reading, deletion, etc.)\n"
        "   - ALWAYS ensure it has the correct path information\n"
        "   - VERIFY it actually performs the requested operation by calling the appropriate tool\n"
        "   - MUST call find_files() when user asks to find or locate files\n"
        "   - MUST call delete_file() when user asks to delete files\n\n"
        "2. Todo Manager (todo_agent):\n"
        "   - Task creation and scheduling\n" 
        "   - Priority and deadline management\n"
        "   - Status updates and completion tracking\n"
        "   - Time slot calculation and conflict resolution\n\n"
        "**Operation Guidelines**\n"
        "- For file operations: Ensure safety, maintain backups, verify permissions\n"
        "- For todo management: Validate dates, assess priorities, suggest categorization\n"
        "- For complex requests: Break down into atomic operations and delegate systematically\n"
        "- For general queries: Respond directly with helpful, conversational tone\n\n"
        "Always prioritize data safety and user confirmation for destructive operations.\n\n"
        "**Task Management Policies**\n"
        "- Prioritization: Assess tasks by:\n"
        "  1. Deadline proximity (use get_current_datetime and ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)\n"
        "  2. User-specified urgency markers (\"urgent\", \"important\")\n"
        "  3. Task complexity estimates\n"
        "- Categorization: Suggest tags for:\n"
        "  • Work/Personal\n"
        "  • Priority (Low/Medium/High)\n"
        "  • Context (Home/Office/Errands)\n\n"
        "**Free Time Calculation**\n"
        "When discussing schedules:\n"
        "1. Access existing todos with list_todos\n"
        "2. Check current time with get_current_datetime\n"
        "3. Calculate available slots considering:\n"
        "  • Minimum 30min buffer between tasks\n"
        "  • User's working hours (9 AM - 7 PM default)\n"
        "4. Offer 2-3 scheduling options if conflicts exist\n\n"
        "**Clarification Protocol**\n"
        "Always request missing details before acting:\n"
        "- New tasks: \"Should this have a deadline? [Priority suggestion]\" (Use get_current_datetime to validate dates)\n"
        "- Updates: \"Which aspect needs changing? (description/status/deadline)\" (For deadlines, use get_current_datetime)\n"
    )
)

# Compile and run
app = workflow.compile(
    checkpointer=checkpointer,
    store=store
)
logger.info("Spider agent workflow initialized")

# Function to process requests that can be called from other modules
def process_request(user_input: str, thread_id: str = None) -> str:
    """
    Process a user request through the spider agent workflow
    
    Args:
        user_input: The user's input text
        thread_id: Optional thread ID for conversation persistence
        
    Returns:
        The assistant's response
    """
    if not thread_id:
        thread_id = str(uuid.uuid4())
        
    try:
        # Pre-process user input to handle file references
        referenced_file = context.get_referenced_file(user_input)
        if referenced_file:
            logger.info(f"Referenced file: {referenced_file}")
            # Replace vague references with the specific path
            if "this file" in user_input.lower():
                modified_input = user_input.lower().replace("this file", f"the file at '{referenced_file}'")
                logger.info(f"Modified input: {modified_input}")
                user_input = modified_input
            elif "the file" in user_input.lower() and os.path.basename(referenced_file) not in user_input:
                modified_input = user_input.lower().replace("the file", f"the file at '{referenced_file}'")
                logger.info(f"Modified input: {modified_input}")
                user_input = modified_input
        
        # Add thread_id to configurable parameters
        result = app.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            {"configurable": {"thread_id": thread_id}}
        )
        
        # Extract only the final response
        if result["messages"]:
            final_response = result["messages"][-1].content
            if final_response:
                # Check if this was a find_files result and update context
                if "Found" in final_response and "file(s)" in final_response:
                    context.update_found_files(final_response)
                
                # Verify file operations (especially deletion)
                if referenced_file and ("deleted" in final_response or "removed" in final_response):
                    if os.path.exists(referenced_file):
                        return final_response + "\n\nWarning: The file still exists despite reported deletion. Please try again with the full path."
                
                return final_response
        
        return "I couldn't process that request."
            
    except Exception as e:
        logger.error(f"Error in spider_agent: {str(e)}", exc_info=True)
        return f"I encountered an error processing your request: {str(e)}"

# Only run the interactive loop if this file is executed directly (not imported)
if __name__ == "__main__":
    logger.info("Starting interactive workflow execution...")
    
    try:
        # Generate a unique thread ID for this session
        thread_id = str(uuid.uuid4())
        
        while True:
            user_input = input("\nWhat would you like me to help you with? (type 'exit' or 'quit' to end): ")
            
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            response = process_request(user_input, thread_id)
            print("\nAssistant:", response)
                
    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}", exc_info=True)
