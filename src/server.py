from flask import Flask, abort, request, Response, stream_with_context, jsonify
from flask_restx import Api, Resource
from flask_jwt_extended import create_access_token
import os
import requests
import json
import psycopg2

from qwc_services_core.auth import auth_manager, optional_auth, get_identity, get_username
from qwc_services_core.tenant_handler import TenantHandler
from qwc_services_core.runtime_config import RuntimeConfig


# Flask application
app = Flask(__name__)
api = Api(app, version='1.0', title='Print API',
          description='API for QWC Print service',
          default_label='Print operations', doc='/api/')

# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

auth = auth_manager(app, api)


tenant_handler = TenantHandler(app.logger)
config_handler = RuntimeConfig("print", app.logger)


# routes
@api.route('/<path:mapid>')
@api.param('mapid', 'The WMS service map name')
class Print(Resource):
    @api.doc('print')
    @optional_auth
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
    @api.param('CONTENT_DISPOSITION', 'Content disposition mode, either inline or attachment', _in='formData')
    def post(self, mapid):
        """Submit query

        Return map print
        """
        tenant = tenant_handler.tenant()
        config = config_handler.tenant_config(tenant)

        identity = get_identity()

        ogc_service_url = config.get(
            'ogc_service_url', 'http://localhost:5013/')
        print_pdf_filename = config.get('print_pdf_filename')
        qgs_postfix = config.get('qgs_postfix', '')
        label_queries_config = config.get('label_queries', [])
        label_values_config = config.get('label_values', [])

        post_params = dict(request.form.items())
        app.logger.info("POST params: %s" % post_params)

        content_disposition = post_params.get(
            'CONTENT_DISPOSITION', 'attachment')

        if 'CONTENT_DISPOSITION' in post_params:
            del post_params['CONTENT_DISPOSITION']

        params = {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetPrint"
        }
        # NOTE: normalize parameter keys to upper case
        params.update({k.upper(): v for k, v in post_params.items()})

        # add fields from custom label queries
        for label_config in label_queries_config:
            conn = psycopg2.connect(label_config["db_url"])
            sql = label_config["query"].replace(
                "$username$", "'%s'" % (get_username(identity) or "")
            )
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.close()
            if row:
                for idx, param in enumerate(label_config['params']):
                    params[param] = row[idx]
            conn.close()

        for label_val in label_values_config:
            params[label_val["field"]] = label_val["value"].replace("$username$", "%s" % (get_username(identity) or ""))

        # forward to OGC service
        headers = {}
        if identity:
            # add authorization headers for forwarding identity
            app.logger.debug(
                "Adding authorization headers for identity '%s'" % get_username(identity)
            )
            access_token = create_access_token(identity)
            headers['Authorization'] = "Bearer " + access_token

        if tenant_handler.tenant_header:
            headers[tenant_handler.tenant_header] = request.headers.get(
                tenant_handler.tenant_header)
        # Forward origin to OGC service
        headers['origin'] = request.origin

        url = ogc_service_url.rstrip("/") + "/" + mapid + qgs_postfix
        app.logger.info("Forwarding request to %s\n%s" % (url, params))
        req = requests.post(url, timeout=120, data=params, headers=headers)

        response = Response(
            stream_with_context(
                req.iter_content(chunk_size=1024)
            ), status=req.status_code
        )
        response.headers['content-type'] = req.headers['content-type']
        if req.headers['content-type'] == 'application/pdf':
            filename = print_pdf_filename or (mapid + '.pdf')
            response.headers['content-disposition'] = content_disposition + \
                '; filename=' + filename

        return response


""" readyness probe endpoint """
@app.route("/ready", methods=['GET'])
def ready():
    return jsonify({"status": "OK"})


""" liveness probe endpoint """
@app.route("/healthz", methods=['GET'])
def healthz():
    return jsonify({"status": "OK"})


# local webserver
if __name__ == '__main__':
    print("Starting GetPrint service...")
    from flask_cors import CORS
    CORS(app)
    app.run(host='localhost', port=5019, debug=True)
