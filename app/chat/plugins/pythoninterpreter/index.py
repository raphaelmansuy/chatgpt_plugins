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
        The code is executed in a docker container with python 3.8.5. 
        BeautifulSoup4 is installed in the container.
        Sympy 1.12 is installed in the container to support symbolic math.
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
                    "description": "Python code which needs to be executed. The code MUST print the result on stdout."
                }
            }
        }
        return parameters


    def execute(self, **kwargs) -> Dict:
        client = docker.from_env()
        code = kwargs['code']

        # read the requirements in the current directory
        # to calculate the current directory with can use the current file (__file__) path
        pathRequirements = os.path.join(os.path.dirname(__file__), "requirements.txt")

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
