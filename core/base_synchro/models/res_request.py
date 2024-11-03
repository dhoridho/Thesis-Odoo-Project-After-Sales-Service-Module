# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResRequest(models.Model):
    _name = "res.request"
    _order = "date desc"
    _description = "Request"

    name = fields.Char("Subject", required=True)
    date = fields.Datetime("Date")
    act_from = fields.Many2one("res.users", "From User")
    act_to = fields.Many2one("res.users", "To User")
    body = fields.Text("Request")
    res_request_lines = fields.One2many('res.request.detail', 'res_request_id', string='Request Detail', readonly=True)

class ResRequestDetail(models.Model):
    _name = "res.request.detail"
    _description = "Request Detail"

    # name = fields.Char("Subject", required=True)
    res_request_id = fields.Many2one('res.request', string='Request', auto_join=True, ondelete="cascade")
    module_name = fields.Char("Module Name")
    source_id = fields.Char("Source ID")
    source_doc_no = fields.Char("Source Document No")
    dest_id = fields.Char("Destination ID")
    dest_doc_no = fields.Char("Destination Document No")

