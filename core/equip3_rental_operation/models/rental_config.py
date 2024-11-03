from odoo import api, fields, models, _
from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    rental = fields.Boolean('Rental')
    is_rental_order_approval_matrix = fields.Boolean('Is Rental Oeder Approval Matrix')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    rental_order_expiry_date = fields.Integer(string='Default Expiry Date')
    rental = fields.Boolean(string="Rental", related='company_id.rental', readonly=False)
    is_rental_order_approval_matrix = fields.Boolean(related='company_id.is_rental_order_approval_matrix', readonly=False, string='Is Rental Oeder Approval Matrix')
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(rental_order_expiry_date=int(get_param('equip3_rental_operation.rental_order_expiry_date')),)
        return res
        
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
		# we store the repr of the values, since the value of the parameter is a required string
        set_param('equip3_rental_operation.rental_order_expiry_date', self.rental_order_expiry_date)