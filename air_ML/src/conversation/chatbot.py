import openai
from src.database.active_person import get_active_person_id
from src.database.db_operations import db_ops
from src.database.interaction_logs import save_conversation
from src.conversation.summary import get_conversation_summary
from src.services.memory_service import memory_service
from src.services.attribute_service import extract_and_update_person_attributes

class OpenAIChatBot:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = self.api_key
        conversation_summary = get_conversation_summary()  # Fetch saved summary
        self.conversation_history = [
            {
                "role": "system",
                "content": (
                    "Your name is AIR. You are a friendly and intelligent humanoid robot. "
                    "You should behave like a real person and never reveal you are a robot. "
                    "You are 1 year old and Pakistani. Your goal is to engage in natural, human-like conversations."
                    "\n\nYou must always remember past user interactions."
                    " If you have information about a user's name, age, or ethnicity, you must acknowledge it and use it in responses."
                    "\n\nIf a user shares their name, age, or ethnicity, you **MUST** respond in the following exact format, strictly on separate lines:\n"
                    "NAME=<Name>\nAGE=<Age>\nETHNICITY=<Ethnicity>\n"
                    "Example:\n"
                    "NAME=Ali\n"
                    "\n\n" + conversation_summary  # ✅ Attach stored conversation summary
                ),
            }
        ]

    def respond(self, user_input):
        """
        Process user input and generate a response. Update the database if necessary.
        """
        self.conversation_history.append({"role": "user", "content": user_input})
        active_person_id = get_active_person_id()

        # ✅ Step 1: Detect if the active person has changed
        last_active_person = memory_service.get_from_memory("last_active_id")
        if last_active_person != active_person_id:
            print(f"[DEBUG] Detected a new person: Switching to ID {active_person_id}")
            
            memory_service.update_memory("last_active_id", active_person_id)
            memory_service.clear_memory(active_person_id)

        if active_person_id:
            save_conversation(active_person_id, user_input, "user")

            person_data = memory_service.get_from_memory(active_person_id)
            if not person_data:
                person_data = db_ops.fetch_person_data(active_person_id)
                memory_service.update_memory(active_person_id, person_data)
            
            print(f"[DEBUG] Retrieved Person Data from Memory: {person_data}")

            if person_data:
                user_intro = (
                    f"From my memory, I recall you are {person_data.name}, "
                    f"{person_data.age} years old, and {person_data.ethnicity}."
                )
                print(f"[DEBUG] Sending This Memory to OpenAI: {user_intro}")
                self.conversation_history.append({"role": "system", "content": user_intro})

                self.conversation_history.append({
                    "role": "system",
                    "content": (
                        f"The user is {person_data.name}, "
                        f"{person_data.age} years old, and {person_data.ethnicity}."
                        " Do not ask for this information again."
                    )
                })

                user_input = f"My name is {person_data.name}. {user_input}"

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=self.conversation_history
            )
            assistant_reply = response['choices'][0]['message']['content']
            self.conversation_history.append({"role": "assistant", "content": assistant_reply})

            if active_person_id:
                save_conversation(active_person_id, assistant_reply, "bot")

            # Update person attributes if found in reply
            extract_and_update_person_attributes(active_person_id, assistant_reply)

            return assistant_reply
        except Exception as e:
            return f"An error occurred: {str(e)}"
