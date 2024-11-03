# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    commission_partner_ids = fields.Many2many("res.partner", "partner_invoice_commission_rel", "invoice_id", "partner_id", "Commission For")
    commission_ids = fields.One2many('acs.hms.commission', 'invoice_id', 'Sales Commission')
    commission_type = fields.Selection([
        ('automatic', 'Automatic'),
        ('fix_amount', 'On Fix Amount'),
    ], string='Commission Type', default='automatic', required=True)
    commission_created = fields.Boolean("Commission Finalized")
    commission_on = fields.Float('Commission On')
    hospital_invoice_type = fields.Selection(selection_add=[('commission', 'Commission')])


    @api.onchange('amount_untaxed')
    def onchange_total_amount(self):
        if self.company_id.commission_on_invoice_amount:
            self.commission_on = self.amount_untaxed

    @api.onchange('ref_physician_id')
    def onchange_ref_physician(self):
        if self.ref_physician_id and self.ref_physician_id.provide_commission:
            self.commission_partner_ids = [(4, self.ref_physician_id.id)]

    @api.onchange('physician_id')
    def onchange_physician(self):
        if self.physician_id:
            #ACS NOTE: no need but sudo do not work for portal access.
            physician = self.env['hms.physician'].sudo().search([('id','=',self.sudo().physician_id.id)])
            if physician.provide_commission:
                self.commission_partner_ids = [(4, physician.partner_id.id)]

    def create_partner_commission(self, partner, amount, commission_on):
        Commission = self.env['acs.hms.commission']
        commission_line = Commission.search([('partner_id','=',partner.id),('invoice_id','=',self.id)], limit=1)
        if commission_line:
            commission_line.write({
                'commission_amount': amount,
                'commission_on': commission_on,
            })
        else:
            Commission.create({
                'partner_id': partner.id,
                'commission_amount': amount,
                'commission_on': commission_on,
                'invoice_id': self.id,
            })            

    def compute_partner_commission(self, partner):
        amount = commission_on = 0
        Rule = self.env['acs.commission.rule']
        
        for line in self.invoice_line_ids:
            if line.product_id:
                matching_rule = False
                product_tmpl_id = line.product_id.product_tmpl_id.id
                product_categ_id = line.product_id.categ_id.id
                if partner.commission_rule_ids:
                    partner_commission_ids = partner.commission_rule_ids.ids
                    matching_rule = Rule.search([('id','in',partner_commission_ids),
                        ('product_id','=',product_tmpl_id)], limit=1)
                    if not matching_rule:
                        matching_rule = Rule.search([('id','in',partner_commission_ids),
                        ('product_category_id','=',product_categ_id)], limit=1)

                if not matching_rule and partner.commission_role_id:
                    role_commission_ids = partner.commission_role_id.commission_rule_ids.ids
                    matching_rule = Rule.search([('id','in', role_commission_ids),
                        ('product_id','=',product_tmpl_id)], limit=1)
                    if not matching_rule:
                        matching_rule = Rule.search([('id','in', role_commission_ids),
                        ('product_category_id','=',product_categ_id)], limit=1)

                if matching_rule:
                    amount += (matching_rule.percentage * line.price_subtotal)/100
                    commission_on += line.price_subtotal

                elif partner.commission_percentage:
                    amount += (partner.commission_percentage * line.price_subtotal)/100
                    commission_on += line.price_subtotal

            self.create_partner_commission(partner, amount, commission_on)
        return amount

    def update_commission_values(self):
        Commission = self.env['acs.hms.commission']
        for rec in self:
            if rec.commission_type=='automatic':
                for partner in rec.commission_partner_ids:
                    self.compute_partner_commission(partner)
            else:
                if rec.commission_on==0:
                    raise UserError(_("Please Set Amount to calculate Commission"))

                for partner in rec.commission_partner_ids:
                    amount = (partner.commission_percentage * self.commission_on)/100
                    self.create_partner_commission(partner, amount, self.commission_on)

            #remove extra lines
            commission_line = Commission.search([('partner_id','not in',rec.commission_partner_ids.ids),('invoice_id','=',self.id)])
            commission_line.sudo().unlink()

    def finalize_commission(self):
        for rec in self:
            if not rec.commission_ids:
                raise UserError(_("No Commission Lines to Finalize! Please create them first."))
            rec.commission_created = True
            rec.commission_ids.action_done()

    def action_post(self):
        for rec in self:
            if rec.commission_partner_ids:
                if not rec.commission_ids:
                    rec.update_commission_values()
                if rec.commission_ids and not rec.commission_created:
                    rec.finalize_commission()
        return super(AccountMove, self).action_post()