from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        manufacturing_plan_conf_menu = self.env.ref("equip3_manuf_operations.con_mrp_plan_menu")
        manufacturing_order_conf_menu = self.env.ref("equip3_manuf_operations.con_mrp_order_menu")
        manufacturing_approval_matrix_conf_menu = self.env.ref("equip3_manuf_operations.con_approval_matrix_menu")
        for company in self:
            if not company == self.env.company:
                continue
            manufacturing_plan_conf_menu.active = company.manufacturing_plan_conf
            manufacturing_order_conf_menu.active = company.manufacturing_order_conf
            manufacturing_approval_matrix_conf_menu.active = company.manufacturing_plan_conf or company.manufacturing_order_conf or company.production_record_conf
        return res

    def _create_unbuild_sequence(self):
        unbuild_vals = []
        for company in self:
            unbuild_vals.append({
                'name': 'Unbuild',
                'code': 'mrp.unbuild',
                'company_id': company.id,
                'prefix': 'UBR/%(y)s/%(month)s/%(day)s/',
                'padding': 3,
                'number_next': 1,
                'number_increment': 1,
                'use_date_range': True
            })
        if unbuild_vals:
            self.env['ir.sequence'].create(unbuild_vals)
