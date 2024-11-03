from odoo import models, fields, api, _

class WarehouseLocationTable(models.Model):
    _name = 'warehouse.location.table'

    project_id = fields.Many2one('project.project', srting='Project')
    internal_location = fields.Many2one('stock.location','Internal Location')
    sequence = fields.Integer(string="Sequence", default=1)
    sr_no = fields.Integer(string="Priority", compute="_sequence_ref")

