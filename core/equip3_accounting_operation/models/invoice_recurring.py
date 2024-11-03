# -*- coding: utf-8 -*-
from odoo import models, fields, api,tools, _
from odoo.exceptions import UserError, ValidationError

class InvoiceRecurring(models.Model):
    _inherit = 'invoice.recurring'

    @api.model
    def _domain_partner_id(self):
        domain = [('company_id','in',[self.env.company.id, False])]
        move_type = self._context.get('default_type') or False
        if move_type:
            if move_type in ['out_invoice','out_refund','out_receipt']:
                domain += [('is_customer','=',True)]
            elif move_type in ['in_invoice','in_refund','in_receipt']:
                domain += [('is_vendor','=',True)]
        return domain

    partner_id = fields.Many2one('res.partner', domain=_domain_partner_id)


    def unlink(self):
        for rec in self:
            if rec.state not in ['draft','cancel']:
                raise UserError(_('You can not delete a recurring invoice which is not in draft or cancel state.'))
        return super(InvoiceRecurring, self).unlink()