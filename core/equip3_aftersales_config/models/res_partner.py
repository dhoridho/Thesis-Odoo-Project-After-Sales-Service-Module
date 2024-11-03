from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    delivery_type_id = fields.Many2one('delivery.type.sale', string='Delivery Type')
    delivery_type = fields.Selection([
        ('delivery_before_payment', 'Delivery Before Payment'),
        ('delivery_after_payment', 'Delivery After Payment'),
    ], string='Delivery Type')
    customer_segmentation_id = fields.Many2one('customer.segmentation.sale', string='Segmentation')
    alias = fields.Char('Alias')


    @api.onchange('vat')
    def _onchange_vat(self):
        for rec in self:
            if rec.vat:
                res_partner = self.env['res.partner'].search([('is_customer','=',True)])
                for partner in res_partner:
                    if rec.vat == partner.vat:
                        rec.vat = None
                        raise ValidationError('This NPWP already existed on another Customer !')

