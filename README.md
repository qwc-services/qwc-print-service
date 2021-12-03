[![](https://github.com/qwc-services/qwc-print-service/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-print-service/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-print-service?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-print-service)

QWC Print service
=================

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
    "qgis_server_version": "3.4.1",
    "print_pdf_filename": "qwc.pdf",
    "label_queries": [
      {
        "db_url": "postgresql:///?service=fachdaten",
        "query": "SELECT 'Bearbeiter/in: ' ||  vorname || ' ' || nachname FROM benutzer WHERE username = $username$",
        "params": [
          "NAME"
        ]
      }
    ]
  },
  "resources": {
    "print_templates": [
      {
        "template": "A4 hoch"
      }
    ]
  }
}
```

`label_queries` is a configuration for additional query parameters to inject into the
WMS `GetPrint` request.

The contents is expected to be

    {
      "label_queries": [{
        "db_url": "<db_url>",
        "query": "<query>",
        "params": ["<ParamName1>", ...]
      },{
        ...
      }],
    }

where:

* `query` is an arbitrary query, returning exactly one row. The `$username$` placeholder can be used to inject the current username.
* `params` is an array of parameter names to inject. The same number of parameters as number of returned values by the query must be specified.


### Environment variables

Config options in the config file can be overridden by equivalent uppercase environment variables.

| Variable                   | Description                                   |
|----------------------------|-----------------------------------------------|
| `OGC_SERVICE_URL`          | OGC Service URL                               |
| `QGIS_SERVER_VERSION`      | QGIS Server version (e.g. `2.18.19`, `3.4.1`) |


Development
-----------

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements.txt

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

    export CONFIG_PATH=../qwc-docker/volumes/config

Configure environment:

    echo FLASK_ENV=development >.flaskenv

Start local service:

    python server.py
