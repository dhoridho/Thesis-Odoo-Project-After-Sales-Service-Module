
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning

class VendorDeposit(models.Model):
    _inherit = 'vendor.deposit'

    partner_id = fields.Many2one(required=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    filter_branch_ids = fields.Many2many('res.branch', string="Branch", compute='_compute_branch_ids')
    move_id = fields.Many2one(required=False)
    is_cash_advance = fields.Boolean(string='Is Cash Advance', default=False)
    return_cash_advance_ids = fields.Many2many('account.move', 'return_cash_advance_move_rel', 'move_id', 'deposit_id', string='Return Cash Advances')


    @api.model
    def create(self, vals):
        if 'is_cash_advance' in vals:
            if 'deposit_reconcile_journal_id' in vals and not vals['deposit_reconcile_journal_id'] or 'journal_id' in vals and not vals['journal_id'] or 'deposit_account_id' in vals and not vals['deposit_account_id']:
                raise ValidationError("Please fill the reconcile journal, payment method, or advance account fields on setting!")

        res = super(VendorDeposit, self).create(vals)
        return res

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        self._compute_branch_ids()

    def _compute_branch_ids(self):
        user = self.env.user
        branch_ids = user.branch_ids + user.branch_id
        for rec in self:
            rec.filter_branch_ids = [(6, 0, branch_ids.ids)]

    def action_pay_cash_advance(self):
        for record in self:
            ref = 'Cash Advance ' + (record.communication or '')
            name = 'Cash Advance ' + (record.name or '')  
            if not record.journal_id.payment_credit_account_id.id:
                raise Warning("Payment Method Credit Account Not Found!")
            debit_vals = {
                    'debit': abs(record.amount),
                    'date': record.payment_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': record.deposit_account_id.id,
                    'analytic_tag_ids': record.account_tag_ids.ids,
                }
            credit_vals = {
                    'debit': 0.0,
                    'date': record.payment_date,
                    'name': name,
                    'credit': abs(record.amount),
                    'account_id': record.journal_id.payment_credit_account_id.id,
                    'analytic_tag_ids': record.account_tag_ids.ids,
                }
            vals = {
                'ref': ref,
                'date': record.payment_date,
                'journal_id': record.journal_id.id,
                'branch_id': record.branch_id.id,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move_id = self.env['account.move'].create(vals)
            move_id.post()
            record.move_id = move_id.id
            record.remaining_amount = record.amount
            record.write({'state': 'post'})


    def action_convert_expense(self):
        context = dict(self.env.context) or {}
        context.update({'default_deposit_type' : 'cash_expense'})

        return{
            'name': 'Expense',
            'type': 'ir.actions.act_window',
            'res_model': 'convert.revenue',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_return_cash_advance(self):
        pass

    def action_cancel_cash_advance(self):
        for record in self:
            if record.amount != record.remaining_amount:
                raise ValidationError(_("Cannot cancel Cash Advance! There are already transaction reconcile with this transaction."))
            else:
                record.move_id.button_draft()
                record.move_id.button_cancel()
                record.write({'state' : 'cancelled'})

    @api.model
    def default_get(self, fields):
        ICP = self.env['ir.config_parameter'].sudo()
        res = super(VendorDeposit, self).default_get(fields)
        if res.get('is_cash_advance'):
            res['deposit_reconcile_journal_id'] = int(ICP.get_param('deposit_reconcile_journal_id'))
            res['journal_id'] = int(ICP.get_param('journal_id'))
            res['deposit_account_id'] = int(ICP.get_param('deposit_account_id'))
        return res



class ConvertToRevenue(models.TransientModel):
    _inherit = 'convert.revenue'

    deposit_type = fields.Selection(selection_add=[('cash_expense', 'Cash Expense')])
    expenses_account_id = fields.Many2one('account.account', "Expense Account")

    def action_confirm(self):
        if self.deposit_type == "cash_expense":
            deposit_id = self.env['vendor.deposit'].browse(self._context.get('active_ids'))
            ref = 'Convert to Expense ' + (deposit_id.communication or '')
            name = 'Convert to Expense ' + (deposit_id.name or '')
            debit_vals = {
                    'debit': abs(deposit_id.remaining_amount),
                    'date': self.date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': self.expenses_account_id.id,
                    'analytic_tag_ids': deposit_id.account_tag_ids.ids,
                }
            credit_vals = {
                    'debit': 0.0,
                    'date': self.date,
                    'name': name,
                    'credit': abs(deposit_id.remaining_amount),
                    'account_id': deposit_id.deposit_account_id.id,
                    'analytic_tag_ids': deposit_id.account_tag_ids.ids,
                }
            vals = {
                'ref': ref,
                'date': self.date,
                'journal_id': deposit_id.deposit_reconcile_journal_id.id,
                'branch_id': deposit_id.branch_id.id,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move_id = self.env['account.move'].create(vals)
            move_id.post()
            deposit_id.write({
                'remaining_amount': 0,
                'state': 'converted'
            })
        else:
            return super(ConvertToRevenue, self).action_confirm()
