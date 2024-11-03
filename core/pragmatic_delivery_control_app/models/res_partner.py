from odoo import models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def geo_localize_custom(self):
        partners = self.search([('partner_latitude', '=', False), ('partner_longitude', '=', False)])

        for record in partners:
            record.geo_localize()

    def geo_localize_update(self):
        partners = self.search([])

        for record in partners:
            record.geo_localize()