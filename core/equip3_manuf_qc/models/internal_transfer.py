from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InternalTransferInheritQC(models.Model):
    _inherit = 'internal.transfer'
    
    quality_check_id = fields.Many2one(comodel_name='sh.quality.check', string='QC')
    
    @api.model
    def create(self, vals):
        res = super(InternalTransferInheritQC, self).create(vals)
        if vals.get('quality_check_id'):
            quality_check_obj = self.env['sh.quality.check'].browse(vals.get('quality_check_id'))
            quality_check_obj.write({'state': 'transfer'})
        return res


    @api.onchange('source_location_id')
    def onchange_location(self):
        if self.quality_check_id and self.source_location_id:
            available_product = self.env['stock.quant'].search([('product_id', '=', self.quality_check_id.product_id.id)]).filtered(lambda x: x.location_id.id == self.source_location_id.id)
            if not available_product:
                raise ValidationError("Product doesn't exist in %s, please select another warehouse" % self.source_warehouse_id.name)