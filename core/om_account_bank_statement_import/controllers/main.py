from odoo import http
from odoo.http import request
import os


class DownloadTemplateController(http.Controller):

    @http.route('/om_account_bank_statement_import/static/src/xlsx/bank_statement_import_template.xlsx', type='http', auth='public')
    def download_bank_statement_import_template(self, **kw):
        bank_statement_import_template_path = os.path.join(os.path.dirname(__file__), 'static/src/xlsx/bank_statement_import_template.xlsx')
        headers = [('Content-Type', 'application/vnd.ms-excel'),
                   ('Content-Disposition', 'attachment; filename=bank_statement_import_template.xlsx;')]
        return request.make_response(open(bank_statement_import_template_path, 'rb').read(), headers=headers, stat=os.stat(bank_statement_import_template_path))
