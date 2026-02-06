[![](https://github.com/qwc-services/qwc-print-service/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-print-service/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-print-service?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-print-service)

QWC Print service
=================

Forwards a print request to the OGC service, allowing injecting additional GetPrint WMS parameters (i.e. layout user labels).

Configuration
-------------

The static config files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

### JSON config

* [JSON schema](schemas/qwc-print-service.json)
* File location: `$CONFIG_PATH/<tenant>/printConfig.json`

Example:
```json
{
  "$schema": "https://raw.githubusercontent.com/qwc-services/qwc-print-service/master/schemas/qwc-print-service.json",
  "service": "print",
  "config": {
    "ogc_service_url": "http://localhost:5013/ows/",
    "print_pdf_filename": "qwc.pdf",
    "label_queries": [
      {
        "db_url": "postgresql:///?service=fachdaten",
        "query": "SELECT 'Bearbeiter/in: ' ||  vorname || ' ' || nachname FROM benutzer WHERE username = $username$",
        "params": [
          "NAME"
        ]
      }
    ],
    "label_values": [
      {
        "field": "USERNAME",
        "value": "$username$"
      }
    ]
  }
}
```

`label_queries` allows configuring additional parameters to inject into the WMS `GetPrint` request, which will be computed from a DB query
The format is as follows:

    "label_queries": [
      {
        "db_url": "<db_url>",
        "query": "<query>",
        "params": ["<ParamName1>", ...]
      },{
        ...
      }
    ]

where:

* `query` is an arbitrary query, returning exactly one row. The `$username$` placeholder can be used to inject the current username.
* `params` is an array of parameter names to inject. The same number of parameters as number of returned values by the query must be specified.

Similarly, `label_values` allows configuring additional static parameters to inject into the WMS `GetPrint` request.
The format is as follows:

    "label_values": [
      {
        "field": "<ParamName1>",
        "value": "<value>"
      },{
        ...
      }
    ]

### Environment variables

Config options in the config file can be overridden by equivalent uppercase environment variables.


Run locally
-----------

Install dependencies and run:

    export CONFIG_PATH=<CONFIG_PATH>
    uv run src/server.py

To use configs from a `qwc-docker` setup, set `CONFIG_PATH=<...>/qwc-docker/volumes/config`.

Set `FLASK_DEBUG=1` for additional debug output.

Set `FLASK_RUN_PORT=<port>` to change the default port (default: `5000`).

API documentation:

    http://localhost:$FLASK_RUN_PORT/api/

Docker usage
------------

The Docker image is published on [Dockerhub](https://hub.docker.com/r/sourcepole/qwc-print-service).

See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).
