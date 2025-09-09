from odoo import models, fields, api
from odoo.exceptions import UserError

class MainModel(models.Model):
    _name = 'main.model'

    name = fields.Char('Name', required=True)
    state_id = fields.Many2one('state.state', 'State', readonly=True, default=1)

    @api.constrains('name')
    def _check_name_uniq(self):
        for main in self:
            if main.name:
                main_ids = self.search([('name', '=', main.name)])
                if len(main_ids) > 1:
                    raise UserError(f"Name {main.name} is not unique.")


    def open_main_wizard(self):
        """Open the technician assignment wizard"""
        return {
            'name': 'Change Sequence',
            'type': 'ir.actions.act_window',
            'res_model': 'main.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    # def create

