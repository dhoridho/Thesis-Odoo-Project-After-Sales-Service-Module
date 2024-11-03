from odoo import models, fields, api, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    # to override type selection since subcontracting boms determined from boolean can_be_subcontracting
    bom_type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'Kit')], 'New BoM Type',
        default='normal', required=True)

    can_be_subcontracted = fields.Boolean(string='Subcontracted')
    use_subcontracting = fields.Boolean(related='company_id.use_subcontracting')
    subcontracting_product_id = fields.Many2one('product.product', string='Subcontracting Service Product', domain="[('type', '=', 'service')]")
    # subcontractor_ids = fields.Many2many('res.partner', domain="[('company_id','=',company_id),('vendor_sequence','!=',False)]")
    subcontractor_ids = fields.Many2many('res.partner', domain="[('company_id','=',company_id)]")

    @api.onchange('bom_type')
    def _onchange_bom_type(self):
        self.type = self.bom_type
