from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def change_service_account(self):
        account_ids = [
            ('equip3_purchase_masterdata', 'service_expense_account_account_data'), 
            ('equip3_purchase_masterdata', 'accrued_payable_account_account_data'),
        ]
        for module, xml_id in account_ids:
            account_id = self.env.ref('%s.%s' % (module, xml_id), raise_if_not_found=False)
            if not account_id:
                continue
            account_move_lines = self.env['account.move.line'].sudo().search([('account_id', '=', account_id.id)])
            new_account_id = self.env.ref('equip3_inventory_masterdata.%s' % xml_id)
            for move_line in account_move_lines:
                move_line.sudo().write({'account_id': new_account_id.id})

            property_ids = self.env['ir.property'].sudo().search([
                ('value_reference', '=', 'account.account,%s' % account_id.id)
            ])
            for prop in property_ids:
                prop.write({'value_reference': 'account.account,%s' % new_account_id.id})
