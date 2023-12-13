import os
import unittest

from flask import Response
from flask.testing import FlaskClient
from flask_jwt_extended import JWTManager

import server
JWTManager(server.app)


class ApiTestCase(unittest.TestCase):
    """Test case for server API"""

    def setUp(self):
        server.app.testing = True
        self.app = FlaskClient(server.app, Response)

    def tearDown(self):
        pass

    # submit query
    def test_print(self):
        params = {
            'DPI': 300,
            'SRS': 'EPSG:2056',
            'TEMPLATE': 'A4 Landscape',
            'FORMAT': 'PDF',
            'TRANSPARENT': 'true',
            'LAYERS': 'countries,states_provinces,country_names,geographic_lines',
            'OPACITIES': '255,127,192',
            'COLORS': ',,',
            'MAP0:LAYERS': 'countries,states_provinces,country_names,geographic_lines',
            'MAP0:SCALE': 12500000,
            'MAP0:EXTENT': '-375000,4812500,2375000,7187500',
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
        response = self.app.post('/ows/qwc_demo', data=params)
        self.assertEqual(200, response.status_code, "Status code is not OK")
