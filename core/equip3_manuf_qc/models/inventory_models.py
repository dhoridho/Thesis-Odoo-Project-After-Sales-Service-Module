from odoo import models, fields, api


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    mrp_quality_check_id = fields.Many2one('sh.mrp.quality.check', string='MRP Quality Check')

    def action_validate(self):
        res = super(StockScrap, self).action_validate()
        for record in self:
            if record.mrp_quality_check_id:
                record.mrp_quality_check_id.write({'state': 'scrap'})
        return res


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    mrp_quality_check_id = fields.Many2one('sh.mrp.quality.check', string='MRP Quality Check')

    def action_validate(self):
        res = super(RepairOrder, self).action_validate()
        for record in self:
            if record.mrp_quality_check_id:
                record.mrp_quality_check_id.write({'state': 'repair'})
        return res


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    mrp_quality_check_id = fields.Many2one('sh.mrp.quality.check', string='MRP Quality Check')

    @api.model
    def create(self, vals):
        records = super(InternalTransfer, self).create(vals)
        for record in records:
            if record.mrp_quality_check_id:
                record.mrp_quality_check_id.write({'state': 'transfer'})
        return records
