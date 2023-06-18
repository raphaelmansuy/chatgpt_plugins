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
        This plugin executes the provided Python code within a Docker container, leveraging Python version 3.8.5.
       
        The python code MUST ALWAYS print the result on stdout at the end of the execution with print(result). 

        If not print result is provided, the plugin will return an error.

        It guarantees the return of execution results via stdout, ensuring easy accessibility and readability of the output.
       
        The environment within the Docker container comes pre-installed with BeautifulSoup4 for parsing HTML and XML documents, and Sympy 1.12 for conducting symbolic mathematical computations.
        At the completion of the code execution, the resultant output will be printed to stdout using the print(result) command. This ensures that the outcome of your Python code is always displayed, facilitating immediate access and review
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
                    "description": "Python code which needs to be executed. The python code MUST ALWAYS print the result on stdout at the end of the execution with print(result). If no print result is provided, the plugin will return an error."
                }
            }
        }
        return parameters

    def execute(self, **kwargs) -> Dict:
        client = docker.from_env()
        code = kwargs['code']

        # read the requirements in the current directory
        # to calculate the current directory with can use the current file (__file__) path
        pathRequirements = os.path.join(
            os.path.dirname(__file__), "requirements.txt")

        print(pathRequirements)

        requirements = None
        if os.path.exists(pathRequirements):
            with open(pathRequirements) as f:
                requirements = f.read()

        # print requirements if present
        if requirements:
            print("Requirements:")
            print(requirements)
        else:
            print("No requirements.txt found")

        # print code if present
        if code:
            print("Code:")
            print(code)

        # Create temporary files for code and requirements
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_code, \
                tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_req:

            temp_code.write(code.encode())
            temp_code.close()  # Close the file so the container can read it

            if requirements:
                temp_req.write(requirements.encode())
                temp_req.close()

            # The command to execute in the Docker container
            commands = []
            if requirements:
                commands.append(
                    f"pip install -r /requirements/{os.path.basename(temp_req.name)} 1> /dev/null")
            commands.append(f"python /code/{os.path.basename(temp_code.name)}")
            command = " && ".join(commands)

            try:
                # Mount the temporary files to the Docker container and run it
                volumes = {temp_code.name: {
                    "bind": f"/code/{os.path.basename(temp_code.name)}", "mode": "ro"}}
                if requirements:
                    volumes[temp_req.name] = {
                        "bind": f"/requirements/{os.path.basename(temp_req.name)}", "mode": "ro"}

                result = client.containers.run(
                    "python:3.8",  # Docker image with Python
                    command=["/bin/bash", "-c", command],
                    volumes=volumes,
                    remove=True,  # remove the container when done
                )
            except docker.errors.ContainerError as e:
                return {"error": str(e)}
            except docker.errors.ImageNotFound as e:
                return {"error": str(e)}
            except docker.errors.APIError as e:
                return {"error": str(e)}
            finally:
                # Make sure to clean up the temporary files even if an error occurs
                os.unlink(temp_code.name)
                if requirements:
                    os.unlink(temp_req.name)

        if not result:
            return {'error': 'No result written to stdout. Please print result on stdout'}
        return {"result": result.decode("utf-8")}
