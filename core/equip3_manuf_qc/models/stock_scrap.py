from odoo import models, fields, api

class StockScrapQcInherit(models.Model):
    _inherit = 'stock.scrap'
    
    quality_check_id = fields.Many2one(comodel_name='sh.quality.check', string='QC')
    
    
    def action_validate(self):
        res = super(StockScrapQcInherit, self).action_validate()
        if self.quality_check_id:
            quality_check_obj = self.env['sh.quality.check'].browse(self.quality_check_id.id)
            quality_check_obj.write({'state': 'scrap'})
        return res
