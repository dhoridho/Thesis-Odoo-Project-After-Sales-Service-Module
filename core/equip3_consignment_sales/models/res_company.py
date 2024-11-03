from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    is_consignment_sales = fields.Boolean(string="Is Consignment Sales", default=False)

    @api.model
    def create(self, vals):
        self.env.context = dict(self._context)
        self.env.context.update({'from_company': True})
        res = super().create(vals)
        return res
