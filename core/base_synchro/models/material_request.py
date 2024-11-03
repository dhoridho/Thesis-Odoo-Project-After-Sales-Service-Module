from odoo import api, fields, models, _


class MaterialRequest(models.Model):
    _inherit = 'material.request'

    base_sync = fields.Boolean("Base Sync", default=False)
    
    def generate_sequence(self):
        material_request = self.env["material.request"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for mr in material_request:
            if mr.base_sync:
                mr.name = self.env["ir.sequence"].next_by_code("material.request")
                mr.base_sync = False

        result = {
            "name": "Material Request Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "material.request",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", material_request.ids)],
            "target": "current",
        }
        return result