from . import models
from . import wizard

import odoo, re, json
from odoo import api, SUPERUSER_ID
from odoo.http import Response, JsonRequest, SessionExpiredException, AuthenticationError, serialize_exception, werkzeug, date_utils, _logger

XML_ID = "equip3_hashmicro_ui._assets_primary_variables"
SCSS_URL = "/equip3_hashmicro_ui/static/src/scss/colors.scss"


def _reset_scss_values(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['equip3_hashmicro_ui.scss_editor'].reset_values(SCSS_URL, XML_ID)

class NewJsonRequest(JsonRequest):

    def _handle_exception(self, exception):

        """Called within an except block to allow converting exceptions
           to arbitrary responses. Anything returned (except None) will
           be used as response."""
        try:
            return super(JsonRequest, self)._handle_exception(exception)
        except Exception:
            if not isinstance(exception, SessionExpiredException):
                if exception.args and exception.args[0] == "bus.Bus not available in test mode":
                    _logger.info(exception)
                elif isinstance(exception, (odoo.exceptions.UserError, werkzeug.exceptions.NotFound)):
                    _logger.warning(exception)
                else:
                    _logger.exception("Exception during JSON request handling.")
            error = {
                'code': 200,
                'message': "HashMicro Server Logs:",
                'data': serialize_exception(exception),
            }
            if isinstance(exception, werkzeug.exceptions.NotFound):
                error['http_status'] = 404
                error['code'] = 404
                error['message'] = "404: Not Found"
            if isinstance(exception, AuthenticationError):
                error['code'] = 100
                error['message'] = "HashMicro Session Invalid"
            if isinstance(exception, SessionExpiredException):
                error['code'] = 100
                error['message'] = "HashMicro Session Expired"

            if isinstance(error['data'], dict) and 'debug' in error['data']:
                def _replacer(matchobj):
                    m = matchobj.group(0)
                    if m[0] == 'O':
                        return 'Hashmicro'
                    return 'hashmicro'
                error['data']['debug'] = re.sub(r'\b[Oo]doo\b', _replacer, str(error['data']['debug']))
            
            return self._json_response(error=error)


def _post_load_hook():
    for method in ('_handle_exception', ):
        method_origin = method + '_origin'
        setattr(JsonRequest, method_origin, getattr(JsonRequest, method)) 
        setattr(JsonRequest, method, getattr(NewJsonRequest, method)) 

def _uninstall_hook(cr, registry):
    _reset_scss_values(cr, registry)
    for method in ('_handle_exception', ):
        method_origin = method + '_origin'
        if hasattr(JsonRequest, method_origin):
            setattr(JsonRequest, method, getattr(JsonRequest, method_origin)) 
