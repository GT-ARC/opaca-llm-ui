# Tests

The SAGE backend is tested with pytest. These tests are located in the `Backend/test` directory. The tests are part of the SAGE CI. These tests are checking the overall functionality of SAGE, not its performance. For performance tests, please refer to the [benchmarks](benchmarks.md).

## Backend (FastAPI)

### 🚀 How to run tests

1. Navigate into the `/Backend` directory
   ```bash
   cd Backend
   ```
2. Install additional test dependencies
   ```bash
   pip install -r test/requirements.txt
   ```
3. Run tests
   ```bash
   python -m pytest
   ```

### 🛠️ Test Contents

Currently, only the Backend is tested. This is done by using the pytest framework. The test covers most of the API endpoints defined in `Backend/src/server.py`. This includes:

- **admin**: Tests whether admin actions are performed correctly in combination with a user client session.
- **config**: Checks if the configuration can be set and reset.
- **files**: Tests the file upload behavior.
- **mcp**: Tests if MCP servers can be added and removed.
- **methods**: Tests the task-solving methods of SAGE to function properly.
- **prompts**: Tests the addition and removal of custom prompts as well as resetting prompts to defaults.