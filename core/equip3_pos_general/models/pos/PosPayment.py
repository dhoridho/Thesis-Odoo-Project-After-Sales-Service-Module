# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
 
    is_receivables_show = fields.Boolean('Is field Receivables Show', compute='_compute_is_receivables_show', store=False)
    
    @api.depends('company_id', 'receivable_account_id')
    def _compute_is_receivables_show(self):
        for rec in self:
            company = rec.company_id
            if not company:
                company = self.env.company
            rec.is_receivables_show = company.is_pos_receivable

    def restrict_create_another_payment_cash(self):
        res_ids = [p.id for p in self]
        cash_count = len([ p for p in self if p.is_cash_count])
        cash_count += self.env[self._name].search_count([('is_cash_count','=',True), ('id','not in',res_ids)])
        if cash_count > 1:
            raise ValidationError(_('Cannot create another payment method Cash'))

        for rec in self:
            if rec.is_cash_count and rec.receivable_account_id and rec.cash_journal_id and rec.cash_journal_id.default_account_id:
                if rec.receivable_account_id.id == rec.cash_journal_id.default_account_id.id:
                    raise ValidationError(_('Unable to save data because the same Account Journal is used for both the Intermediary Account and the Cash Journal. Please change one of the Account Journals to proceed.'))

    @api.model
    def create(self, vals):
        res = super(PosPaymentMethod, self).create(vals)
        res.restrict_create_another_payment_cash()
        return res

    def write(self, vals):
        res = super(PosPaymentMethod, self).write(vals)
        if 'active' not in vals:
            self.restrict_create_another_payment_cash()
        return res