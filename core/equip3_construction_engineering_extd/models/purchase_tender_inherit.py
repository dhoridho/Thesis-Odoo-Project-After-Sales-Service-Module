from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PurchaseTender(models.Model):
    _inherit = 'purchase.agreement'

    is_engineering = fields.Boolean('Engineering', store=True)

    @api.onchange('project')
    def onchange_project_enginerring(self):
        if self.project:
            # self.is_engineering = False
            if self.project.construction_type == 'engineering':
                self.is_engineering = True
            else:
                self.is_engineering = False
    
    def tender_lines(self, rec, current_date, rec_line):
        res = super(PurchaseTender, self).tender_lines(rec, current_date, rec_line)
        res['finish_good_id'] = rec_line.finish_good_id.id

        return res
    
    def vendor_prepare(self, rec, line_ids, picking, vendor):
        res = super(PurchaseTender, self).vendor_prepare(rec, line_ids, picking, vendor)
        res['is_engineering'] = rec.is_engineering

        return res

class VariableLine(models.Model):
    _inherit = 'pt.variable.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class MaterialLine(models.Model):
    _inherit = 'material.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class ServiceLine(models.Model):
    _inherit = 'service.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class PAEquipmentLine(models.Model):
    _inherit = 'pa.equipment.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class LabourLine(models.Model):
    _inherit = 'labour.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    
class OverheadLine(models.Model):
    _inherit = 'overhead.line'
    
    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class PurchaseTenderLine(models.Model):
    _inherit = 'purchase.agreement.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
