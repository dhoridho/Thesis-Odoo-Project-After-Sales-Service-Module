from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, values):
        res = super(ResCompany, self).write(values)
        kitchen_menu = self.env.ref("equip3_kitchen_accessright_settings.menu_kitchen_root")
        for company in self:
            if company == self.env.company:
                kitchen_menu.active = company.central_kitchen
        return res
