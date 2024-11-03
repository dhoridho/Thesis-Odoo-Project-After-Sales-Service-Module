from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        assembly_menu = self.env.ref("equip3_assembly_accessright_settings.menu_assembly_root")
        for company in self:
            if company == self.env.company:
                assembly_menu.active = company.assembly
        return res
