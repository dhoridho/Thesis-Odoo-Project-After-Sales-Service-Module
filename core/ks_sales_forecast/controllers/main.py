import json
from odoo import http
from odoo.tools import html_escape
from odoo.http import content_disposition, request
from odoo.addons.web.controllers.main import _serialize_exception


class ReportController(http.Controller):

    @http.route('/ks_sale_forecast_xlsx_report', type='http', auth='user', methods=['POST'], csrf=False)
    def ks_get_report_xlsx(self, model, options, output_format, token, report_name, **kw):
        ks_id = int(options)
        ks_report_obj = request.env[model].browse(ks_id)
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[('Content-Type', self.ks_content_type()),
                             ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                             ]
                )
                ks_report_obj.ks_create_xlsx_report(response)
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

    def ks_content_type(self):
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
