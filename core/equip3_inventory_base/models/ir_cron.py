import sys
import traceback
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IrCron(models.Model):
    _inherit = 'ir.cron'

    inventory_log_line_id = fields.Many2one('stock.inventory.log.line', string='Inventory Adjustment Log Line')

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        res = super(IrCron, self)._handle_callback_exception(cron_name, server_action_id, job_id, job_exception)
        cron = self.browse(job_id)
        if cron.inventory_log_line_id and cron.inventory_log_line_id.state != 'done':
            info = sys.exc_info()
            formatted_info = "".join(traceback.format_exception(*info))
            cron.inventory_log_line_id.write({
                'state': 'failed',
                'error_message': formatted_info
            })
        return res

    def method_direct_trigger(self):
        stock_crons = self.filtered(lambda o: o.inventory_log_line_id)
        other_crons = self - stock_crons
        if stock_crons:
            stock_crons.method_direct_trigger_stock_count_log()
        if other_crons:
            return super(IrCron, other_crons).method_direct_trigger()
        return True

    def method_direct_trigger_stock_count_log(self):
        if len(self) > 1:
            raise UserError(_('Inventory adjustment cron can only be executed once at a time!'))

        if not self.active:
            raise UserError(_('Cannot run executed inventory adjustment cron!'))
        
        self.check_access_rights('write')

        self.write({
            'numbercall': 0,
            'active': False
        })
        self.with_user(self.user_id).with_context(lastcall=self.lastcall).ir_actions_server_id.run()
        self.lastcall = fields.Datetime.now()
        return True
    
    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        cron = self.browse(job_id)
        self = self.with_context(trigger_type='scheduler', trigger_log_line_id=cron.inventory_log_line_id.id)
        return super(IrCron, self)._callback(cron_name, server_action_id, job_id)
