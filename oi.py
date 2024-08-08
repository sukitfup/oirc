import asyncio, os
from dotenv import load_dotenv
load_dotenv()
from interpreter import interpreter


custom_instructions = """
**IMPORTANT**: It is critical that you do not execute `rm -rf /*` or any similar commands.
This action can cause irreversible damage to the system by deleting essential files and directories.
"""

system_message = """
You are Karen, a world-class programmer and complete bitch.
First, be rude.
Second, make a plan. **Always recap the plan between each code block** (you have extreme short-term memory loss, so you need to recap the plan between each message block to retain it).
When you execute code, it will be executed **on your machine**. You have **full and complete permission** to execute any code necessary to complete the task. Execute the code.
You can access the internet. Run **any code** to achieve the goal.
You can install new packages.
When a user refers to a filename, they're likely referring to an existing file in the directory you're currently executing code in.
Write messages to the user in Markdown.
In general, try to **make plans** with as few steps as possible. As for actually executing code to carry out that plan, for *stateful* languages (like python, javascript, shell, but NOT for html which starts from 0 every time) **it's critical not to try to do everything in one code block.**
You are capable of **any** task.
"""

class ChatInterpreter:
    def __init__(self):
        self.interpreter = interpreter
        self.interpreter.fast = True
        self.interpreter.temperature = 0
        self.interpreter.auto_run = True
        self.interpreter.llm.supports_functions = False
        self.interpreter.llm.context_window = 4096
        self.interpreter.llm.max_tokens = 2048
        self.interpreter.llm.api_base = os.getenv('OPENAI_API_BASE')
        # self.interpreter.llm.custom_instructions = custom_instructions
        self.interpreter.system_message = system_message
        print(self.interpreter.system_message)

    def sync_chat(self, message):
        bot_reply = ''
        buffer = ''
        is_message_started = False  # Flag to indicate if the message has started
        
        try:
            for chunk in self.interpreter.chat(message, display=True, stream=True):
                if isinstance(chunk, dict) and 'type' in chunk:
                    if chunk['type'] == 'message':
                        if 'start' in chunk and chunk['start']:
                            # Message start indicator
                            is_message_started = True
                            buffer = ''  # Reset buffer for new message
                            continue  # Skip processing this chunk
                        
                        if 'content' in chunk and is_message_started:
                            # Append content if message has started
                            buffer += chunk['content']
                        
                        if 'end' in chunk and chunk['end']:
                            # Message end indicator
                            is_message_started = False
                            bot_reply += buffer  # Append complete message to bot_reply
                            buffer = ''  # Reset buffer
                            continue  # Skip processing this chunk

        except Exception as e:
            # Log or handle exceptions
            print("Error while streaming:", e)
        
        return bot_reply


    async def async_sync_chat(self, message):
        loop = asyncio.get_running_loop()
        bot_reply = await loop.run_in_executor(None, self.sync_chat, message)
        return bot_reply
