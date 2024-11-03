from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    dedicated_material_consumption = fields.Boolean('Dedicated Material Consumption')

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        manufacturing_pr_conf_menu = self.env.ref("equip3_manuf_operations_contd.con_mrp_consumption_menu")
        manufacturing_pr_conf_menu.active = self.env.company.production_record_conf
        return res
