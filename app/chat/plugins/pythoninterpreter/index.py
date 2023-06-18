import docker
from typing import Dict
from app.chat.plugins.plugin import PluginInterface
import tempfile
import os

class PythonInterpreterPlugin(PluginInterface):
    def get_name(self) -> str:
        """
        return the name of the plugin (should be snake case)
        """
        return "python"

    def get_description(self) -> str:
        return """
        Execute the given python code return the result from stdout. The result of execution of the code must printed on stdout at the end of the execution. Please print result on stdout.
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
                "code": {
                    "type": "string",
                    "description": "Python code which needs to be executed. The result of execution of the code must printed on stdout. Please print result on stdout."
                },
            }
        }
        return parameters

    def execute(self, **kwargs) -> Dict:
        client = docker.from_env()
        code = kwargs['code']

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp:
            print(code)
            temp.write(code.encode())
            temp.close()  # Close the file so the container can read it

            # Mount the temporary file to the Docker container and run it
            try:
                result = client.containers.run(
                    "python:3.8",  # Docker image with Python
                    # Path inside container
                    command=["python", "/code/temp.py"],
                    # Read-only
                    volumes={temp.name: {
                        "bind": "/code/temp.py", "mode": "ro"}},
                    remove=True,  # remove the container when done
                )
            except docker.errors.ContainerError as e:
                return {"error": str(e)}
            except docker.errors.ImageNotFound as e:
                return {"error": str(e)}
            except docker.errors.APIError as e:
                return {"error": str(e)}
            finally:
                 # Make sure to clean up the temporary file even if an error occurs
                os.unlink(temp.name)

        if not result:
            return {'error': 'No result written to stdout. Please print result on stdout'}
        return {"result": result.decode("utf-8")}
