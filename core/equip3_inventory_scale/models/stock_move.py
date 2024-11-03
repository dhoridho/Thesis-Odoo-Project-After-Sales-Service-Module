from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    def button_scale(self):
        return self.env["ir.actions.actions"]._for_xml_id("equip3_inventory_scale.stock_scale_action")
