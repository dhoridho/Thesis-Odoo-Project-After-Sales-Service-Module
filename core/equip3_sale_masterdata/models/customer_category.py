from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CustomerCategory(models.Model):
    _name = 'customer.category'
    _description = "Customer Category"

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.company)

    @api.constrains('name')
    def _check_existing_record(self):
        for record in self:
            customer_category_id = self.search([('id', '!=', record.id), ('name', 'ilike', record.name)], limit=1)
            if customer_category_id:
                raise ValidationError("Data can't be the same like other category !")