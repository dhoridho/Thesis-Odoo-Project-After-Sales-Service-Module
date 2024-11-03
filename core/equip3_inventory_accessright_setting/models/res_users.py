from odoo import _, api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    warehouse_ids = fields.Many2many('stock.warehouse','user_warehouse_new_rel', 'warehouse_id', 'user_id',string="Allowed Warehouse")
