from app.chat.plugins.plugin import PluginInterface

from typing import Dict, Optional
import requests
import os


class WeatherPlugin(PluginInterface):
    def get_name(self) -> str:
        """
        Returns the name of the plugin (should be snake case)
        """
        return "weather_plugin"
    
    def get_description(self) -> str:
        """
        Returns a brief description of the plugin.
        """
        return "Fetches the current weather information for the given location"
    
    def get_parameters(self) -> Dict[str, Dict[str, str]]:
        """
        Returns the list of parameters to execute this plugin in the form of
        JSON schema as specified in the OpenAI documentation:
        https://platform.openai.com/docs/api-reference/chat/create#chat/create-parameters
        """
        parameters = {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location for which to fetch the weather"
                }
            },
            "required": ["location"]
        }
        return parameters
    
    def execute(self, **kwargs) -> Dict[str, Optional[Dict]]:
        """
        Executes the plugin and returns a JSON response.
        The parameters are passed in the form of kwargs.
        """

        # Get the API key from environment variables
        api_key = os.getenv('WEATHER_API_KEY')
        if api_key is None:
            return {"error": "Weather API key not found in environment variables"}

        # Get the location from kwargs
        location = kwargs.get('location')
        if location is None:
            return {"error": "No location provided"}

        # Construct the API URL
        url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={location}"

        try:
            # Send a GET request to the URL
            response = requests.get(url)

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                weather_data = response.json()

                # Return the weather data
                return {"weather": weather_data}
            else:
                return {"error": f"Unable to fetch weather data, status code: {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
