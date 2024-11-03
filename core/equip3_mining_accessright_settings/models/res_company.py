from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, vals):
        result = super(ResCompany, self).write(vals)
        mining_menu_root = self.env.ref('equip3_mining_accessright_settings.mining_menu_root')
        for company in self:
            if company != self.env.company:
                continue
            mining_menu_root.active = company.mining
        return result
