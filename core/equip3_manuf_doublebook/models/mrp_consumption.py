from odoo import models, fields, api, _


class MrpConsumption(models.Model):
    _name = 'mrp.consumption'
    _inherit = ['mrp.consumption', 'base.synchro.abstract']

    def sync_resequence(self):
        consumptions = self.filtered(lambda o: o.base_sync)
        for consumption in consumptions:
            consumption.name = self.env['ir.sequence'].next_by_code('mrp.consumption')

    def sync_unlink(self):
        consumptions = self.filtered(lambda o: o.base_sync)
        (consumptions.move_raw_ids | consumptions.byproduct_ids | consumptions.move_finished_ids).sync_unlink()
        consumptions.unlink()
