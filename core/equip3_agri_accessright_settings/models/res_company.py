from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, vals):
        result = super(ResCompany, self).write(vals)
        agri_menu_root = self.env.ref('equip3_agri_accessright_settings.menu_agriculture_root')
        for company in self:
            if company != self.env.company:
                continue
            agri_menu_root.active = company.agriculture
        return result
