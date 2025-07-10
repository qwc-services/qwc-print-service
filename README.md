[![](https://github.com/qwc-services/qwc-print-service/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-print-service/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-print-service?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-print-service)

QWC Print service
=================

Forwards a print request to the OGC service, allowing injecting additional GetPrint WMS parameters (i.e. layout user labels).

API documentation:

    http://localhost:5019/api/


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

| Variable                   | Description                                   |
|----------------------------|-----------------------------------------------|
| `OGC_SERVICE_URL`          | OGC Service URL                               |
| `QGIS_SERVER_VERSION`      | QGIS Server version (e.g. `2.18.19`, `3.4.1`) |


Docker usage
------------

See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).


Development
-----------

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

    export CONFIG_PATH=../qwc-docker/volumes/config

Configure environment:

    echo FLASK_ENV=development >.flaskenv

Install dependencies and run service:

    uv run src/server.py
