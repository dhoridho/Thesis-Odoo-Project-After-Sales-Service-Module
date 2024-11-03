from odoo import models, fields, api


class RepairOrderQcInherit(models.Model):
    _inherit = 'repair.order'

    quality_check_id = fields.Many2one(
        comodel_name='sh.quality.check', string='QC')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(RepairOrderQcInherit, self).onchange_partner_id()
        if not self.partner_id.property_product_pricelist:
            self.pricelist_id = self.env['product.pricelist'].search([
                ('company_id', 'in', [self.env.company.id, False]),
            ], limit=1)
        return res

    def action_validate(self):
        res = super(RepairOrderQcInherit, self).action_validate()
        if self.quality_check_id:
            quality_check_obj = self.env['sh.quality.check'].browse(
                self.quality_check_id.id)
            quality_check_obj.write({'state': 'repair'})
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if not self.quality_check_id:
            return super(RepairOrderQcInherit, self)._onchange_company_id()
