
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    stock_scrap_id = fields.Many2one('stock.scrap.request', string="Acccounting")

    @api.model
    def change_other_inventory_account(self):
        account_id = self.env.ref('equip3_inventory_control.data_account_account_other_inventory', raise_if_not_found=False)
        if not account_id:
            return
        account_move_lines = self.env['account.move.line'].sudo().search([('account_id', '=', account_id.id)])
        new_account_id = self.env.ref('equip3_inventory_masterdata.data_account_account_other_inventory')
        for move_line in account_move_lines:
            move_line.sudo().write({'account_id': new_account_id.id})

        property_ids = self.env['ir.property'].sudo().search([
            ('value_reference', '=', 'account.account,%s' % account_id.id)
        ])
        for prop in property_ids:
            prop.write({'value_reference': 'account.account,%s' % new_account_id.id})
