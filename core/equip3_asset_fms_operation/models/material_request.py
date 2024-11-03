from odoo import models, fields, _
from odoo.exceptions import ValidationError


class MaterialRequest(models.Model):
    _inherit = 'material.request'
    
    maintenance_ro_id = fields.Many2one('maintenance.repair.order', string='MRO')
    maintenance_wo_id = fields.Many2one('maintenance.work.order', string='MWO')

    def button_confirm(self):
        for record in self:
            for line in record.product_line:
                if line.quantity <= 0:
                    raise ValidationError("You can not confirm without product quantity or zero quantity of product.")
            record.write({'status': 'confirm'})
        view_id = self.env.ref('equip3_inventory_operation.material_request_form_view').id
        if 'default_schedule_date' in self._context:
            return {
                'name': 'Create Material Request',
                'type': 'ir.actions.act_window',
                'res_model': 'material.request',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'context': {},
            }

    def material_request_done(self):
        show_popup = False
        for line in self.product_line:
            if line.quantity > line.done_qty:
                show_popup = True
        if show_popup:
            return {
                'name': 'Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'show.material.done.popup',
                'view_type': 'form',
                'target': 'new'
            }
        view_id = self.env.ref('equip3_inventory_operation.material_request_form_view').id
        if 'default_schedule_date' in self._context:
            self.write({'status': 'done'})
            return {
                'name': 'Create Material Request',
                'type': 'ir.actions.act_window',
                'res_model': 'material.request',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'context': {},
            }
        else:
            self.write({'status': 'done'})