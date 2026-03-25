# How to Deploy Containers

Agent Containers can be added to an OPACA Runtime Platform, and thus to SAGE, either through OPACA's own Swagger Web UI, or from the Agents view within SAGE.

## OPACA Swagger-UI

1. Open the Swagger-UI of the platform, usually available at http://localhost:8000/swagger-ui/index.html
2. Go to `POST /containers` and paste your container definition as JSON in the request body. For example:
   ```json
   {
      "image": {
         "imageName": "<your-container-name>"
      }
   }
   ```
3. If a UUID was returned, your container was successfully deployed. Otherwise, check the docker logs of your container for any errors.

**Note**: OPACA is also able to pull containers from container registries, such as DockerHub, Github Container Registry, or any private registry the host machine has access to.

### With authentication enabled

1. Go to `POST /login` and paste your OPACA user credentials in the request body
   ```json
   {
     "username": "<username>",
     "password": "<password>"   
   }
   ```
2. If successful, you will receive a Bearer token in the response body.
3. Go to `Authorize` and paste the Bearer token in the `value` field

### Environment Variables

If you need to provide environment variables to your container, you must define and pass them when you deploy the container. The following JSON shows an example where the environment variable `MY_API_KEY` is provided:

```json
{
  "image": {
    "imageName": "<your-container-name>",
    "parameters": [
      {
        "name": "MY_API_KEY",
        "type": "string",
        "required": true,
        "confidential": true,
        "defaultValue": null
      }
    ]
  },
  "arguments": {
    "MY_API_KEY": "<your-api-key>"
  }
}
```

## SAGE-UI

If SAGE is connected to an OPACA Runtime Platform, then the Agents view in the sidebar can be used to start OPACA Agent Containers on that connected platform, provided the user currently logged into SAGE (and thus OPACA) has sufficient privileges. (Starting containers requires a role of "contributor" or higher, whereas other functions can be used with a "user" role, as well.) Users can either specify only the name of the OPACA Container Image, or provide a full JSON specification as with the Swagger UI above. The latter is useful if the container can be parameterized or provides extra-ports, both of which have to be included in the JSON in order to be configured properly when the container is started.

Conversely, running agent containers can also be stopped and removed from the Agents view and OPACA Runtime Platform by clicking the small "x" symbol.

Both starting and stopping containers from within SAGE can be deactivated via the `VITE_CONTAINER_MANAGEMENT` environment variable, which can be useful to prevent container deployment in a public no-auth deployment.

## Developing Agent Containers

For more information about how to develop containers, check out our [OPACA Python SDK](https://github.com/gt-arc/opaca-python-sdk).
