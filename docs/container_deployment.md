# How to deploy containers

## Swagger-UI

1. Open the Swagger-UI of the platform, usually available at http://localhost:8000/swagger-ui/index.html
2. Go to `POST /containers` and paste your container definition as JSON in the request body. For example:
   ```json
   {
      "image": {
         "imageName": "<your-container-name>"
      }
   }
   ```
3. If an uuid was returned, your container was successfully deployed. Otherwise, check the docker logs of your container for any errors.

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

### Developing Agent Containers

For more information about how to develop containers, check out our [OPACA Python SDK](https://github.com/gt-arc/opaca-python-sdk).

## SAGE-UI

Under development