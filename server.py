from flask import Flask, abort, request, Response, stream_with_context
from flask_restplus import Api, Resource
import os
import requests

from external_ows_layers import ExternalOwsLayers


# Flask application
app = Flask(__name__)
api = Api(app, version='1.0', title='GetPrint API',
          description='API for QWC GetPrint service',
          default_label='Print operations', doc='/api/')

# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False


OGC_SERVER_URL = os.environ.get('OGC_SERVICE_URL',
                                'http://localhost:5013/').rstrip("/") + "/"


# routes
@api.route('/<mapid>')
@api.param('mapid', 'The WMS service map name')
class Print(Resource):
    @api.doc('print')
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
        opacities = params.get('OPACITIES', '').split(',')
        colors = params.get('COLORS', '').split(',')

        # extract any external WMS and WFS layers
        external_ows_layers = ExternalOwsLayers(app.logger)
        external_ows_layers.update_params(params, layerparam)

        # forward to QGIS server
        url = OGC_SERVER_URL + mapid
        req = requests.post(url, timeout=120, data=params)
        app.logger.info("Forwarding request to %s\n%s" % (req.url, params))

        response = Response(
            stream_with_context(
                req.iter_content(chunk_size=1024)
            ), status=req.status_code
        )
        response.headers['content-type'] = req.headers['content-type']
        if req.headers['content-type'] == 'application/pdf':
            response.headers['content-disposition'] = \
                'filename=' + mapid + '.' + params['FORMAT']

        return response


# local webserver
if __name__ == '__main__':
    print("Starting GetPrint service...")
    from flask_cors import CORS
    CORS(app)
    app.run(host='localhost', port=5015, debug=True)
