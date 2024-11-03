
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustomerDegreeTrust(models.Model):
    _name = 'customer.degree.trust'
    _description = "Customer Degree Trust"
     
    name = fields.Char(string="Name", required=True)
    overdue_day = fields.Integer(string="Overdue Days")
    no_of_overdue_invoices = fields.Integer(string="Number Of Overdue Invoices")
    index = fields.Integer(string="Index", compute="_compute_index", store=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    @api.depends('overdue_day', 'no_of_overdue_invoices')
    def _compute_index(self):
        for record in self:
            record.index = record.overdue_day * record.no_of_overdue_invoices

    @api.constrains('name', 'index', 'company_id')
    def _check_existing_record(self):
        for record in self:
            customer_degree_trust_id = self.env['customer.degree.trust'].search([
                ('id', '!=', record.id), ('name', 'ilike', record.name), ('index', '=', record.index),
                ('company_id', '=', record.company_id.id)], limit=1)
            if len(customer_degree_trust_id) > 0:
                raise ValidationError("Data can't be the same like other degree of trust !")
