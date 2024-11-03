
from odoo import api , fields , models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_set_vendor_purchase_limit = fields.Boolean(string="Set Vendor Purchase Limit ?")
    vendor_purchase_limit = fields.Float(string="Vendor Purchase Limit")
    vendor_available_purchase_limit = fields.Float(string="Vendor Available Purchase Limit", readonly=True)
    is_set_vendor_onhold = fields.Boolean(string="Set Vendor On Hold (Purchase Limit Exceed)")
    report_pr_template_id = fields.Many2one('ir.actions.report', string="Purchase Request Template",
                                            help="Please select Template report for Purchase Request", domain=[('model', '=', 'purchase.request')])
    type = fields.Selection(selection_add=
        [
         ('invoice', 'Invoice/Bill Address')
        ], string='Address Type',
        default='contact',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")

    @api.model
    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        vendor_purchase_limit =  IrConfigParam.get_param('vendor_purchase_limit', 0)
        # vendor_purchase_limit =  self.env.company.vendor_purchase_limit
        res['vendor_purchase_limit'] = vendor_purchase_limit
        res['vendor_available_purchase_limit'] = vendor_purchase_limit
        return res
