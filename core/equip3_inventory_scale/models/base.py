from odoo import fields, models, api


class Base(models.AbstractModel):
    _inherit = "base"

    def button_scale(self):
        return self.env["ir.actions.actions"]._for_xml_id("equip3_inventory_scale.stock_scale_action")

    def on_scaled(self):
        return
