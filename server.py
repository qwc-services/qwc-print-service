from flask import Flask, abort, request, Response, stream_with_context
from flask_restplus import Api, Resource
from flask_jwt_extended import jwt_optional, get_jwt_identity
import os
import requests
import json
import psycopg2

from qwc_services_core.jwt import jwt_manager
from qwc_services_core.tenant_handler import TenantHandler
from qwc_services_core.runtime_config import RuntimeConfig
from external_ows_layers import ExternalOwsLayers


# Flask application
app = Flask(__name__)
api = Api(app, version='1.0', title='Print API',
          description='API for QWC Print service',
          default_label='Print operations', doc='/api/')

# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

# Setup the Flask-JWT-Extended extension
jwt = jwt_manager(app, api)


tenant_handler = TenantHandler(app.logger)
config_handler = RuntimeConfig("print", app.logger)


# routes
@api.route('/<mapid>')
@api.param('mapid', 'The WMS service map name')
class Print(Resource):
    @api.doc('print')
    @jwt_optional
    @api.param('DPI', 'The print dpi', _in='formData')
    @api.param('SRS', 'The SRS of the specified map extent', _in='formData')
    @api.param('TEMPLATE', 'The print template', _in='formData')
    @api.param('FORMAT', 'The file format for the print output', _in='formData')
    @api.param('TRANSPARENT', 'Whether to use transparent background if possible', _in='formData')
    @api.param('LAYERS', 'The layers list for opacities', _in='formData')
    @api.param('OPACITIES', 'The opacities of the layers to print', _in='formData')
    @api.param('COLORS', 'The colors list for external WFS layers', _in='formData')
    @api.param('map0:LAYERS', 'The layers to print', _in='formData')
    @api.param('map0:SCALE', 'The scale for the specified map', _in='formData')
    @api.param('map0:EXTENT', 'The extent for the specified map', _in='formData')
    @api.param('map0:ROTATION', 'The rotation for the specified map', _in='formData')
    @api.param('map0:GRID_INTERVAL_X', 'The x interval for the grid of the specified map', _in='formData')
    @api.param('map0:GRID_INTERVAL_Y', 'The y interval for the grid of the specified map', _in='formData')
    @api.param('map0:HIGHLIGHT_GEOM', 'The geometries to add to the specified map', _in='formData')
    @api.param('map0:HIGHLIGHT_SYMBOL', 'The styles for the highlight geometries', _in='formData')
    @api.param('map0:HIGHLIGHT_LABELSTRING', 'The label texts for the highlight geometries', _in='formData')
    @api.param('map0:HIGHLIGHT_LABELCOLOR', 'The label colors for the highlight geometries', _in='formData')
    @api.param('map0:HIGHLIGHT_LABELBUFFERCOLOR', 'The label buffer colors for the highlight geometries', _in='formData')
    @api.param('map0:HIGHLIGHT_LABELBUFFERSIZE', 'The label buffer sizes for the highlight geometries', _in='formData')
    @api.param('map0:HIGHLIGHT_LABELSIZE', 'The label sizes for the highlight geometries', _in='formData')
    def post(self, mapid):
        """Submit query

        Return map print
        """
        tenant = tenant_handler.tenant()
        config = config_handler.tenant_config(tenant)

        ogc_service_url = config.get(
            'ogc_service_url', 'http://localhost:5013/')
        print_pdf_filename = config.get('print_pdf_filename')
        qgs_postfix = config.get('qgs_postfix', '')
        qgis_server_version = config.get('qgis_server_version', '2.18.19')
        label_queries_config = config.get('label_queries', [])
        # TODO: read resources

        post_params = dict(request.form.items())
        app.logger.info("POST params: %s" % post_params)

        params = {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetPrint"
        }
        params.update(post_params)

        # normalize parameter keys to upper case
        params = {k.upper(): v for k, v in params.items()}

        # Search layers parameter
        layerparam = None
        for key, value in params.items():
            if key.endswith(":LAYERS"):
                layerparam = key
                break
        if not layerparam:
            abort(400, "Missing <mapName>:LAYERS parameter")

        template = params.get('TEMPLATE')
        layers = params.get(layerparam, '').split(',')
        opacities = params.get('OPACITIES', [])
        if opacities:
            opacities = opacities.split(',')
        colors = params.get('COLORS', '').split(',')

        # extract any external WMS and WFS layers
        external_ows_layers = ExternalOwsLayers(
            qgis_server_version, app.logger)
        external_ows_layers.update_params(params, layerparam)

        # add fields from custom label queries
        for label_config in label_queries_config:
            conn = psycopg2.connect(label_config["db_url"])
            sql = label_config["query"].replace("$username$", "'%s'" % (get_jwt_identity() or ""))
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.close()
            if row:
                for idx, param in enumerate(label_config['params']):
                    params[param] = row[idx]
            conn.close()

        # forward to QGIS server
        url = ogc_service_url.rstrip("/") + "/" + mapid + qgs_postfix
        req = requests.post(url, timeout=120, data=params)
        app.logger.info("Forwarding request to %s\n%s" % (req.url, params))

        response = Response(
            stream_with_context(
                req.iter_content(chunk_size=1024)
            ), status=req.status_code
        )
        response.headers['content-type'] = req.headers['content-type']
        if req.headers['content-type'] == 'application/pdf':
            filename = print_pdf_filename or (mapid + '.pdf')
            response.headers['content-disposition'] = \
                'attachment; filename=' + filename

        return response


# local webserver
if __name__ == '__main__':
    print("Starting GetPrint service...")
    from flask_cors import CORS
    CORS(app)
    app.run(host='localhost', port=5015, debug=True)
