## CLI

### Setup

Before using the CLI, make sure the script is executable:

```bash
chmod +x cli.sh
```

### Usage

```bash
./cli.sh <command> [options]
```

The script changes into `api/`, sets `PYTHONPATH=src`, and delegates to `python -m fury_api.scripts.cli`. Any flags you pass are forwarded untouched.

#### Common examples

- List the latest earthquakes:

  ```bash
  ./cli.sh list-earthquakes
  ```

- Paginate by internal ID:

  ```bash
  ./cli.sh list-earthquakes --after-id 777
  ```

- Pull full details for a specific record:

  ```bash
  ./cli.sh get-earthquake 797
  ```

- Ingest new data from USGS:

  ```bash
  ./cli.sh ingest-earthquakes 2024-01-01 2024-01-02 --min-magnitude 4.0
  ```

- Transform a CIIM Geo image (local file or URL):

  ```bash
  ./cli.sh transform-image https://example.com/image.jpg -o output.png
  ```

### Notes
- For each command you can learn more about it using the help flag (`-h`) e.g:
  - `./cli.sh -h`
  - `./cli.sh list-earthquakes -h`
  - etc
- Environment variables from `api/.env` are still respected because the script runs inside the API project root.
