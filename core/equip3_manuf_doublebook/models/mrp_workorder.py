from odoo import models, fields, api, _


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'base.synchro.abstract']

    base_sync = fields.Boolean()
    base_sync_origin_id = fields.Integer()
    base_sync_last_sync = fields.Datetime(string='Last Synchronized')

    def sync_resequence(self):
        workorders = self.filtered(lambda o: o.base_sync)
        for workorder in workorders:
            workorder.workorder_id = self.env['ir.sequence'].next_by_code('mrp.workorder')
            workorder.consumption_ids.sync_resequence()

    def sync_unlink(self):
        workorders = self.filtered(lambda o: o.base_sync)
        workorders.consumption_ids.sync_unlink()
        workorders.unlink()

    def button_finish_wizard(self):
        res = super(MrpWorkorder, self).button_finish_wizard()
        if self.env.context.get('doublebook', False):
            if res is None:
                consumption = self.consumption_ids.filtered(lambda o: o.state != 'confirm')
            else:
                consumption = self.env['mrp.consumption'].browse(res['res_id'])
            consumption.action_generate_serial()
            consumption.button_confirm()
        return res