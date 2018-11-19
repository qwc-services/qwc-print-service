GetPrint service
======================

API documentation:

    http://localhost:5015/api/


Environment variables
---------------------

| Variable              | Description                                   |
|-----------------------|-----------------------------------------------|
| `OGC_SERVICE_URL`     | OGC Service URL                               |
| `QGIS_SERVER_VERSION` | QGIS Server version (e.g. `2.18.19`, `3.4.1`) |


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
