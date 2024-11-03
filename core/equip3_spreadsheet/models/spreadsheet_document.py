from odoo import models, fields, api


class SpreadsheetDocument(models.Model):
    _name = 'spreadsheet.document'
    _description = 'Spreadsheet Document'

    name = fields.Char(string='Name', required=True)
    raw = fields.Binary(string='File Content (raw)', attachment=False)
    thumbnail = fields.Binary(string='Thumbnail')

    def check_spreadsheet_access(self, operation: str, *, raise_exception=True):
        try:
            self.check_access_rights(operation)
            self.check_access_rule(operation)
        except AccessError as e:
            if raise_exception:
                raise e
            return False
        return True
