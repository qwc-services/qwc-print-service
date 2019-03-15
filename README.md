GetPrint service
======================

API documentation:

    http://localhost:5015/api/


Environment variables
---------------------

| Variable                   | Description                                   |
|----------------------------|-----------------------------------------------|
| `OGC_SERVICE_URL`          | OGC Service URL                               |
| `QGIS_SERVER_VERSION`      | QGIS Server version (e.g. `2.18.19`, `3.4.1`) |
| `QWC_PRINT_SERVICE_CONFIG` | Additional print service configuration file.  |

Print service configuration
---------------------------

The `QWC_PRINT_SERVICE_CONFIG` environment variable can point to a JSON file
which can be used to configure additional query parameters to inject into the
WMS `GetPrint` request.

The contents of the file is expected to be

    {
      "labels": [{
        "service": "<db_service_name>",
        "query": "<query>",
        "params": ["<ParamName1>", ...]
      },{
        ...
      }],
    }

where:

* `service` is a name of known a database connection, i.e. defined in pg_services.conf
* `query` is an arbitrary query, returning exactly one row. The `$username$` placeholder can be used to inject the current username.
* `params` is an array of parameter names to inject. The same number of parameters as number of returned values by the query must be specified.

Development
-----------

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 --system-site-packages .venv

Without system packages:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements.txt
    pip install flask_cors

Start local service:

    OGC_SERVICE_URL=http://localhost:8001/ows/ QGIS_SERVER_VERSION=2.18.19 python server.py
