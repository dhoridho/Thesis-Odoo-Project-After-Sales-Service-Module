from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ActionReplaceParts(models.TransientModel):
    _name = 'action.replace.parts.wizard'
    _description = 'Action Replace Parts'

    parent_equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Parent Equipment')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment')
    serial_no = fields.Char(string='Serial Number', related='equipment_id.serial_no')

    def check_duplicate_part(self):
        existing_equipment_ids = self.env['vehicle.parts'].search([('equipment_id', '=', self.equipment_id.id),('maintenance_equipment_id', '!=', False)], limit=1).maintenance_equipment_id.name
        if existing_equipment_ids:
            raise ValidationError(_('Please choose a different equipment.\n This equipment already exists in "%s"') % (existing_equipment_ids))

    def action_confirm(self):
        self.check_duplicate_part()
        
        active_id = self._context.get('active_id')
        if active_id:
            parts_line = self.env['replacement.parts.line'].browse(active_id)
            parts_line.write({
                'replacement_part_id': self.equipment_id.id,
                'new_part_serial': self.equipment_id.serial_no,
            })
