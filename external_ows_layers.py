import random
import re

import requests


class ExternalOwsLayers:
    """ExternalOwsLayers class

    Helper class to get SLD for external WMS and WFS layers.
    """

    def __init__(self, qgis_server_version, logger):
        """Constructor

        :param Logger logger: Application logger
        """
        self.logger = logger

        # parse QGIS Server version
        parts = qgis_server_version.split('.')
        # [major, minor, rev]
        version = [0, 0, 0]
        for i, part in enumerate(parts):
            try:
                version[i] = int(part)
            except ValueError as e:
                self.logger.error("Error parsing qgis_server_version: %s" % e)
            if i > 2:
                break

        self.qgis_version = version[0] * 10000 + version[1] * 100 + version[2]

    def update_params(self, params, layerparam):
        """Extract external WMS and WFS layers from LAYERS param
        and adjust params accordingly.

        :param obj params: Request parameters
        :param str layerparam: `<mapName>:LAYERS` parameter key
        """
        layers = params.get(layerparam, '').split(',')
        opacities = params.get('OPACITIES', '').split(',')
        colors = params.get('COLORS', '').split(',')

        if self.qgis_version < 30000:
            # QGIS Server 2.x
            sld_body = self.sld_layers(
                layers, colors, opacities, params.get('SRS'), params.get('DPI')
            )
            if sld_body:
                # add external layers as SLD UserLayers
                params['SLD_BODY'] = sld_body
        else:
            # QGIS Server 3.x
            external_wms_params = self.external_wms_layers(
                layerparam, layers, opacities, params.get('SRS')
            )
            # add external layers as EXTERNAL_WMS params
            params.update(external_wms_params)

    def sld_layers(self, layers, colors, opacities, crs, dpi):
        """Extract external WMS and WFS layers from LAYERS param
        and return SLD with RemoteOWS UserLayers.

        :param list(str) layers: List of requested layers
        :param list(str) colors: List of colors for WFS layers
        :param list(str) opacities: List of layer opacities
        :param str crs: Requested CRS
        :param int dpi: Requested DPI
        """
        sld_body = ""

        wms_layer_pattern = re.compile("^wms:(.+)#(.+)$")
        wfs_layer_pattern = re.compile("^wfs:(.+)#(.+)$")

        for i, layer in enumerate(layers):
            m = wms_layer_pattern.match(layer)
            if m is not None:
                name = layer

                # build WMS OnlineResource
                base_url = self.url_with_suffix(m.group(1))
                url = "%sLAYERS=%s&amp;STYLES=&amp;CRS=%s&amp;FORMAT=image/png" % \
                    (base_url, m.group(2), crs)

                # add UserLayer
                sld_body += "<UserLayer>"
                sld_body +=   "<Name>%s</Name>" % name
                sld_body +=   "<RemoteOWS>"
                sld_body +=     "<Service>WMS</Service>"
                sld_body +=     "<OnlineResource xlink:href=\"%s\" />" % url
                sld_body +=   "</RemoteOWS>"
                sld_body += "</UserLayer>"

                continue

            m = wfs_layer_pattern.match(layer)
            if m is not None:
                name = layer
                typename = m.group(2)
                opacity = opacities[i] if i < len(opacities) else ''
                color = colors[i] if i < len(colors) else ''

                # build WFS OnlineResource
                base_url = self.url_with_suffix(m.group(1))
                url = "%sTYPENAME=%s&amp;srsName=%s" % (base_url, typename, crs)

                sld_body += "<UserLayer>"
                sld_body +=   "<Name>%s</Name>" % name
                sld_body +=   "<RemoteOWS>"
                sld_body +=     "<Service>WFS</Service>"
                sld_body +=     "<OnlineResource xlink:href=\"%s\" />" % url
                sld_body +=   "</RemoteOWS>"
                sld_body +=   self.wfs_style(base_url, typename, color,
                                             opacity, dpi)
                sld_body += "</UserLayer>"

                continue

        if sld_body:
            sld_body = "<StyledLayerDescriptor>%s</StyledLayerDescriptor>" % \
                       sld_body

        return sld_body

    def external_wms_layers(self, layerparam, layers, opacities, crs):
        """Extract external WMS layers from LAYERS param and return params
        for EXTERNAL_WMS.

        :param str layerparam: `<mapName>:LAYERS` parameter key
        :param list(str) layers: List of requested layers
        :param list(str) opacities: List of layer opacities
        :param str crs: Requested CRS
        """
        params = {}

        wms_layer_pattern = re.compile("^wms:(.+)#(.+)$")
        wfs_layer_pattern = re.compile("^wfs:(.+)#(.+)$")

        wms_layers = []
        layer_opacities = []
        for i, layer in enumerate(layers):
            m = wms_layer_pattern.match(layer)
            if m is not None:
                # external WMS layer
                # generate name for external layer (A, B, C, ..., AA, BB, ...)
                name = chr(97 + i % 26).upper()
                if i > 26:
                    name *= (i // 26) + 1

                base_url = self.url_with_suffix(m.group(1))
                layers = m.group(2)

                # add params for external WMS layer
                params.update({
                    '%s:url' % name: base_url,
                    '%s:layers' % name: layers,
                    '%s:format' % name: 'image/png',
                    '%s:crs' % name: crs,
                    '%s:styles' % name: '',
                    '%s:dpiMode' % name: 7,
                    '%s:contextualWMSLegend' % name: 0
                })
                # rename layer
                wms_layers.append("EXTERNAL_WMS:%s" % name)

                if i < len(opacities):
                    layer_opacities.append(opacities[i])

                continue

            m = wfs_layer_pattern.match(layer)
            if m is not None:
                # external WFS layer
                self.logger.warning(
                    "External WFS layers not supported in QGIS Server 3.x: %s"
                    % layer
                )

                continue

            # WMS layer from map
            wms_layers.append(layer)
            if i < len(opacities):
                layer_opacities.append(opacities[i])

        params[layerparam] = ','.join(wms_layers)
        params['OPACITIES'] = ','.join(layer_opacities)

        return params

    def url_with_suffix(self, url):
        """Append '?' or '&' to base URL

        :param str url: Base URL
        """
        if not url.endswith('?'):
            if '?' in url:
                url += '&'
            else:
                url += '?'
        return url

    def wfs_style(self, wfs_url, typename, color, opacity, dpi):
        """Return SLD style for geometry type of WFS layer.

        Use automatic style with random color if color is empty or
        geometry type is ambiguous.

        :param str wfs_url: WFS base URL
        :param str typename: WFS layer name
        :param str color: Feature color as hex #rrggbb
        :param str opacity: Layer opacity
        :param int dpi: Requested DPI
        """
        sld_body = ""

        if opacity:
            try:
                opacity = int(opacity)
            except Exception as e:
                opacity = 255
            if opacity < 255:
                # scale to [0:1]
                opacity = opacity/255.0
                if not color:
                    # set random color if transparent
                    color = "#%06x" % random.randint(0, 0xFFFFFF)

        if color:
            # get geometry type from DescribeFeatureType
            url = "%sTYPENAME=%s&SERVICE=WFS&REQUEST=DescribeFeatureType" % \
                (wfs_url, typename)
            response = requests.get(url)

            if "PolygonPropertyType\"" in response.text:
                self.logger.debug(
                    "Using polygon style (%s, %.2f) for %s %s" % (
                        color, opacity or 1.0, wfs_url, typename
                    )
                )
                sld_body = self.polygon_style(color, opacity)
            elif "LineStringPropertyType\"" in response.text:
                self.logger.debug(
                    "Using line style (%s, %.2f) for %s %s" % (
                        color, opacity or 1.0, wfs_url, typename
                    )
                )
                sld_body = self.line_style(color, opacity)
            elif "PointPropertyType\"" in response.text:
                self.logger.debug(
                    "Using point style (%s, %.2f) for %s %s" % (
                        color, opacity or 1.0, wfs_url, typename
                    )
                )
                sld_body = self.point_style(color, opacity, dpi)
            # else use default automatic style

        if not sld_body:
            self.logger.debug(
                "Using default automatic style for %s %s" % (wfs_url, typename)
            )

        return sld_body

    def polygon_style(self, color, opacity):
        """Return SLD style for polygons,

        :param str color: Fill color as hex #rrggbb
        :param float opacity: Layer opacity [0:1]
        """
        sld_body = ""
        sld_body += "<UserStyle>"
        sld_body +=   "<Name></Name>"
        sld_body +=   "<FeatureTypeStyle>"
        sld_body +=     "<Rule>"
        sld_body +=       "<PolygonSymbolizer>"
        sld_body +=         "<Fill>"
        sld_body +=           "<CssParameter name=\"fill\">"
        sld_body +=             color
        sld_body +=           "</CssParameter>"
        if opacity:
            sld_body +=       "<CssParameter name=\"fill-opacity\">"
            sld_body +=         str(opacity)
            sld_body +=       "</CssParameter>"
        sld_body +=         "</Fill>"
        sld_body +=         "<Stroke>"
        sld_body +=           "<CssParameter name=\"stroke\">"
        sld_body +=             "#000000"
        sld_body +=           "</CssParameter>"
        sld_body +=           "<CssParameter name=\"stroke-width\">"
        sld_body +=             "2"
        sld_body +=           "</CssParameter>"
        if opacity:
            sld_body +=       "<CssParameter name=\"stroke-opacity\">"
            sld_body +=         str(opacity)
            sld_body +=       "</CssParameter>"
        sld_body +=         "</Stroke>"
        sld_body +=       "</PolygonSymbolizer>"
        sld_body +=     "</Rule>"
        sld_body +=   "</FeatureTypeStyle>"
        sld_body += "</UserStyle>"

        return sld_body

    def line_style(self, color, opacity):
        """Return SLD style for lines,

        :param str color: Stroke color as hex #rrggbb
        :param float opacity: Layer opacity [0:1]
        """
        sld_body = ""
        sld_body += "<UserStyle>"
        sld_body +=   "<Name></Name>"
        sld_body +=   "<FeatureTypeStyle>"
        sld_body +=     "<Rule>"
        sld_body +=       "<LineSymbolizer>"
        sld_body +=         "<Stroke>"
        sld_body +=           "<CssParameter name=\"stroke\">"
        sld_body +=             color
        sld_body +=           "</CssParameter>"
        sld_body +=           "<CssParameter name=\"stroke-width\">"
        sld_body +=             "2"
        sld_body +=           "</CssParameter>"
        if opacity:
            sld_body +=       "<CssParameter name=\"stroke-opacity\">"
            sld_body +=         str(opacity)
            sld_body +=       "</CssParameter>"
        sld_body +=         "</Stroke>"
        sld_body +=       "</LineSymbolizer>"
        sld_body +=     "</Rule>"
        sld_body +=   "</FeatureTypeStyle>"
        sld_body += "</UserStyle>"

        return sld_body

    def point_style(self, color, opacity, dpi):
        """Return SLD style for points,

        :param str color: Fill color as hex #rrggbb
        :param int dpi: DPI for scaling mark size
        :param float opacity: Layer opacity [0:1]
        """
        if not dpi:
            dpi = 200
        try:
            dpi = int(dpi)
        except Exception as e:
            dpi = 200

        # scale size by dpi
        size = 10 * dpi/96

        sld_body = ""
        sld_body += "<UserStyle>"
        sld_body +=   "<Name></Name>"
        sld_body +=   "<FeatureTypeStyle>"
        sld_body +=     "<Rule>"
        sld_body +=       "<PointSymbolizer>"
        sld_body +=         "<Graphic>"
        sld_body +=           "<Mark>"
        sld_body +=             "<WellKnownName>circle</WellKnownName>"
        sld_body +=             "<Fill>"
        sld_body +=               "<CssParameter name=\"fill\">"
        sld_body +=                 color
        sld_body +=               "</CssParameter>"
        if opacity:
            sld_body +=           "<CssParameter name=\"fill-opacity\">"
            sld_body +=             str(opacity)
            sld_body +=           "</CssParameter>"
        sld_body +=             "</Fill>"
        sld_body +=             "<Stroke>"
        sld_body +=               "<CssParameter name=\"stroke\">"
        sld_body +=                 "#000000"
        sld_body +=               "</CssParameter>"
        sld_body +=               "<CssParameter name=\"stroke-width\">"
        sld_body +=                 "2"
        sld_body +=               "</CssParameter>"
        if opacity:
            sld_body +=           "<CssParameter name=\"stroke-opacity\">"
            sld_body +=             str(opacity)
            sld_body +=           "</CssParameter>"
        sld_body +=             "</Stroke>"
        sld_body +=           "</Mark>"
        sld_body +=           "<Size>"
        sld_body +=             str(size)
        sld_body +=           "</Size>"
        sld_body +=         "</Graphic>"
        sld_body +=       "</PointSymbolizer>"
        sld_body +=     "</Rule>"
        sld_body +=   "</FeatureTypeStyle>"
        sld_body += "</UserStyle>"

        return sld_body
