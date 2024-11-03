from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"

    exchange_id = fields.Many2one('account.invoice.exchange', string='Invoice Exchange')
    exchange_stage = fields.Selection(string='Exchange Status', related='exchange_id.stage')
    exchange_date = fields.Date(string='Received Date', related='exchange_id.date')
    exchange_status = fields.Selection(selection=[
                                                    ('pending', 'Pending Exchange'),
                                                    ('exchanged', 'Exchanged'),
                                                    ('revision', 'Need Revision')
                                                ], string='Exchange Status', compute='exchange_onchange')

    def action_journal_entry_report(self):
        return {
            'name': self.ids,
            'tag': 'je_r',
            'type': 'ir.actions.client',
        }

    @api.depends('exchange_id', 'exchange_stage')
    def exchange_onchange(self):
        for rec in self:
            if rec.exchange_id.stage:
                if rec.exchange_id.stage == 'approved':
                    rec.exchange_status = 'exchanged'
                elif rec.exchange_id.stage == 'confirm':
                    rec.exchange_status = 'pending'
                elif rec.exchange_id.stage == 'rejected':
                    rec.exchange_status = 'revision'
                else:
                    rec.exchange_status = False
            else:
                rec.exchange_status = False


class AccountMoveTemplate(models.Model):
    _inherit = "account.move.template"

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', domain="[('company_id', '=', company_id)]", check_company=True)