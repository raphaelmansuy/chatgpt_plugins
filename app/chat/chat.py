import openai
import requests
import json
from typing import List, Dict
import uuid
from .plugins.plugin import PluginInterface
import yaml
import importlib.util
import os

GPT_MODEL = "gpt-3.5-turbo-0613"  # "gpt-3.5-turbo-16k-0613"

SYSTEM_PROMPT = """
    You are a helpful AI assistant. You answer the user's queries.
    When you are not sure of an answer, you take the help of
    functions provided to you.
    NEVER make up an answer if you don't know, just respond
    with "I don't know" when you don't know.
"""


class Conversation:
    """
    This class represents a conversation with the ChatGPT model.
    It stores the conversation history in the form of a list of messages.
    """

    def __init__(self):
        self.conversation_history: List[Dict] = []

    def add_message(self, role, content):
        message = {"role": role, "content": content}
        self.conversation_history.append(message)


class ChatSession:
    """
    Represents a chat session.
    Each session has a unique id to associate it with the user.
    It holds the conversation history
    and provides functionality to get new response from ChatGPT
    for user query.
    """

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.conversation = Conversation()
        self.plugins: Dict[str, PluginInterface] = {}
        self.load_plugins()
        self.conversation.add_message("system", SYSTEM_PROMPT)

    def load_plugins(self):
        """
        Load plugins from the plugins subdirectory.
        """
        plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
        for root, dirs, files in os.walk(plugins_dir):
            if "manifest.yml" in files:
                with open(os.path.join(root, "manifest.yml"), "r") as f:
                    manifest = yaml.safe_load(f)
                    if not manifest.get('plugin', {}).get('disabled', False):
                        self._import_plugin(manifest['plugin'], root)

    def _import_plugin(self, plugin_manifest, plugin_dir):
        """
        Dynamically import a plugin and register it.
        """
        spec = importlib.util.spec_from_file_location(
            plugin_manifest['main'].replace('.py', ''),
            os.path.join(plugin_dir, plugin_manifest['main'])
        )
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        plugin_class = getattr(plugin_module, plugin_manifest['class'])
        self.register_plugin(plugin_class())

    def register_plugin(self, plugin: PluginInterface):
        """
        Register a plugin for use in this session
        """
        # log the name of the plugins using a logger component
        print(f"Registering plugin: {plugin.get_name()}")
        self.plugins[plugin.get_name()] = plugin

    def get_messages(self) -> List[Dict]:
        """
        Return the list of messages from the current conversation
        """
        if len(self.conversation.conversation_history) == 1:
            return []
        return self.conversation.conversation_history[1:]

    def _get_functions(self) -> List[Dict]:
        """
        Generate the list of functions that can be passed to the chatgpt
        API call.
        """
        return [self._plugin_to_function(p) for p in self.plugins.values()]

    def _plugin_to_function(self, plugin: PluginInterface) -> Dict:
        """
        Convert a plugin to the function call specification as
        required by the ChatGPT API:
        https://platform.openai.com/docs/api-reference/chat/create#chat/create-functions
        """
        function = {
            "name": plugin.get_name(),
            "description": plugin.get_description(),
            "parameters": plugin.get_parameters(),
        }
        return function

    def _execute_plugin(self, func_call) -> str:
        """
        If a plugin exists for the given function call, execute it.
        """
        func_name = func_call.get("name")
        print(f"Executing plugin {func_name}")
        if func_name in self.plugins:
            arguments = json.loads(func_call.get("arguments"))
            plugin = self.plugins[func_name]
            plugin_response = plugin.execute(**arguments)
        else:
            plugin_response = {
                "error": f"No plugin found with name {func_name}"}

        # We need to pass the plugin response back to ChatGPT
        # so that it can process it. In order to do this we
        # need to append the plugin response into the conversation
        # history. However, this is just temporary so we make a
        # copy of the messages and then append to that copy.
        print(f"Response from plugin {func_name}: {plugin_response}")
        messages = list(self.conversation.conversation_history)
        messages.append(
            {
                "role": "function",
                "content": json.dumps(plugin_response),
                "name": func_name,
            }
        )
        next_chatgpt_response = self._chat_completion_request(messages)

        # If ChatGPT is asking for another function call, then
        # we need to call _execute_plugin again. We will keep
        # doing this until ChatGPT keeps returning function_call
        # in its response. Although it might be a good idea to
        # cut it off at some point to avoid an infinite loop where
        # it gets stuck in a plugin loop.
        if next_chatgpt_response.get("function_call"):
            return self._execute_plugin(next_chatgpt_response.get("function_call"))
        return next_chatgpt_response.get("content")

    def get_chatgpt_response(self, user_message: str) -> str:
        """
        For the given user_message,
        get the response from ChatGPT
        """
        self.conversation.add_message("user", user_message)
        try:
            chatgpt_response = self._chat_completion_request(
                self.conversation.conversation_history
            )

            if chatgpt_response.get("function_call"):
                chatgpt_message = self._execute_plugin(
                    chatgpt_response.get("function_call")
                )
            else:
                chatgpt_message = chatgpt_response.get("content")
            self.conversation.add_message("assistant", chatgpt_message)
            return chatgpt_message
        except Exception as e:
            print(e)
            return "something went wrong"

    def _chat_completion_request(self, messages: List[Dict]):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + openai.api_key,
        }
        json_data = {
            "model": GPT_MODEL,
            "messages": messages,
            "temperature": 0.7,
        }
        if self.plugins:
            json_data.update({"functions": self._get_functions()})
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=json_data,
            )
            return response.json()["choices"][0]["message"]
        except Exception as e:
            print("Unable to generate ChatCompletion response")
            print(f"Exception: {e}")
            return e
