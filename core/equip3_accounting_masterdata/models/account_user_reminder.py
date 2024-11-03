
from odoo import api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning


class AccountUserReminder(models.Model):
    _name = "account.user.reminder"
    _description = 'Account USer Reminder'
    
    name = fields.Char(string="Name")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('res.branch', string='Branch')
    account_line_ids = fields.One2many('account.user.reminder.lines', 'account_line_id', string="Account Line")
    reminder_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('bill', 'Bill')
    ], string="Invoice Type")
    
    @api.constrains('branch_id')
    def _check_existing_record(self):
        for record in self:
            if record.branch_id:
                account_user_reminder_id = self.search([('branch_id', '=', record.branch_id.id), ('reminder_type', '=', record.reminder_type), ('id', '!=', record.id)], limit=1)
                if account_user_reminder_id:
                    raise ValidationError("The reminder user configuration is already set. Please check the record or change the branch!")
    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.account_line_ids:
                line.sequence = current_sequence
                current_sequence += 1
    
class AccountUserReminderLines(models.Model):
    _name = "account.user.reminder.lines"
    _description = 'Account USer Reminder Lines'
    
    @api.model
    def default_get(self, fields):
        res = super(AccountUserReminderLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'account_line_ids' in context_keys:
                if len(self._context.get('account_line_ids')) > 0:
                    next_sequence = len(self._context.get('account_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res
    
    account_line_id = fields.Many2one('account.user.reminder', string="Account Lines")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    sequence = fields.Integer(string="Sequence")   
    sequence2 = fields.Integer(string="No.", related="sequence", readonly=True, store=True) 
    
    def unlink(self):
        approval = self.account_line_id
        res = super(AccountUserReminderLines, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(AccountUserReminderLines, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.account_line_id._reset_sequence()
        return res