# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import Response


def patch_json_response():

    _old_json_response = http.JsonRequest._json_response

    def _json_response(self, result=None, error=None):
        if result and isinstance(result, Response):
            out = result
        else:
            out = _old_json_response(self, result=result, error=error)
        return out

    http.JsonRequest._json_response = _json_response
