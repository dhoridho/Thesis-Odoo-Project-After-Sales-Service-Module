# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request, Response


class Home(http.Controller):

    @http.route('/print-bluetooth', type='http', auth="public", csrf=False, website=True)
    def print_bluetooth(self, **post):
        return Response(json.dumps(request.params), headers={'Access-Control-Allow-Origin': '*'})