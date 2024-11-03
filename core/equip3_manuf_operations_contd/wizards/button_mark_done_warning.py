from odoo import models, fields


class ButtonMarkDoneWarning(models.TransientModel):
    _name = 'button.mark.done.warning'
    _description = 'Button Mark Done Warning'

    message = fields.Text(string='Text')
    production_id = fields.Many2one('mrp.production')

    def open_self(self):
        action = {
            'name': 'Warning',
            'type': 'ir.actions.act_window',
            'res_model': 'button.mark.done.warning',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }
        return action

    def action_confirm(self):
        return self.production_id.with_context(skip_all_wo_done=True).button_mark_done()
