from app.chat.plugins.plugin import PluginInterface
from typing import Dict
import requests

class WolframAlphaPlugin(PluginInterface):
    def get_name(self) -> str:
        """
        return the name of the plugin (should be snake case)
        """
        return "wolfram_alpha"
    
    def get_description(self) -> str:
        return """
        Access computation, math, curated knowledge & real-time data through Wolfram|Alpha and Wolfram Language.
        """
    
    def get_parameters(self) -> Dict:
        """
        Return the list of parameters to execute this plugin in
        the form of JSON schema as specified in the
        OpenAI documentation:
        https://platform.openai.com/docs/api-reference/chat/create#chat/create-parameters
        """
        parameters = {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The input expression or query to send to Wolfram Alpha"
                },
                "assumption": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "The assumption to use, passed back from a previous query with the same input."
                }
            },
            "required": ["input"]
        }
        return parameters
    
    def execute(self, **kwargs) -> Dict:
        """
        Execute the plugin and return a JSON response.
        The parameters are passed in the form of kwargs
        """
        print(kwargs)
        try:
            # You would need to implement the actual API call to Wolfram Alpha here.
            # The following is a placeholder and won't actually work.
            # Replace this with the actual API implementation using the requests library or similar.
            url = "https://www.wolframalpha.com/api/v1/llm-api"
            headers = {"Authorization": "Bearer 43e40eb7b346427b9a3da3050a6c58c5"}
            params = {"input": kwargs["input"]}
            if "assumption" in kwargs:
                params["assumption"] = kwargs["assumption"]
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return {"result": response.json()}
        except Exception as e:
            return {"error": str(e)}
