import os
import unittest
from urllib.parse import urlparse, parse_qs, unquote

from flask import Response, json
from flask.testing import FlaskClient
from flask_jwt_extended import JWTManager, create_access_token

import server


class ApiTestCase(unittest.TestCase):
    """Test case for server API"""

    def setUp(self):
        server.app.testing = True
        self.app = FlaskClient(server.app, Response)
        JWTManager(server.app)

    def tearDown(self):
        pass

    def jwtHeader(self):
        with server.app.test_request_context():
            access_token = create_access_token('test')
        return {'Authorization': 'Bearer {}'.format(access_token)}

    # submit query
    def test_print(self):
        params = {
            'DPI': 300,
            'SRS': 'EPSG:2056',
            'TEMPLATE': 'A4_portrait',
            'FORMAT': 'PDF',
            'TRANSPARENT': 1,
            'LAYERS': 'test_point,test_poly,wms:http://wms.geo.admim.ch#test',
            'OPACITIES': '255,127,192',
            'COLORS': ',,',
            'MAP0:LAYERS': 'test_point,test_poly,wms:http://wms.geo.admim.ch#test',
            'MAP0:SCALE': 250000,
            'MAP0:EXTENT': '2600087,1219011,2618587,1243911',
            'MAP0:ROTATION': 0,
            'MAP0:GRID_INTERVAL_X': 500,
            'MAP0:GRID_INTERVAL_Y': 500,
            'MAP0:HIGHLIGHT_GEOM': '',
            'MAP0:HIGHLIGHT_SYMBOL': '',
            'MAP0:HIGHLIGHT_LABELSTRING': '',
            'MAP0:HIGHLIGHT_LABELCOLOR': '',
            'MAP0:HIGHLIGHT_LABELBUFFERCOLOR': '',
            'MAP0:HIGHLIGHT_LABELBUFFERSIZE': '',
            'MAP0:HIGHLIGHT_LABELSIZE': ''
        }
        response = self.app.post('/somap', data=params, headers=self.jwtHeader())
        self.assertEqual(200, response.status_code, "Status code is not OK")
        data = json.loads(response.data)
        self.assertEqual('somap_print', data['path'], 'Print project name mismatch')
        self.assertEqual('POST', data['method'], 'Method mismatch')
        print_params = dict([list(map(unquote, param.split("=", 1))) for param in data['data'].split("&")])
        for param in params.keys():
            self.assertTrue(param in print_params, "Parameter %s missing in response" % param)
            self.assertEqual(print_params[param], str(params[param]), "Parameter %s mismatch" % param)
        self.assertTrue("SLD_BODY" in print_params)
