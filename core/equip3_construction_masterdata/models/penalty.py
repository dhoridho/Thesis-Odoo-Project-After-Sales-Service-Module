# -*- coding: utf-8 -*-

import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PenaltyCost(models.Model):
    _name = 'construction.penalty'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Penalty'
    _check_company_auto = True
    

    name = fields.Char(string='Name', required=True)
    penalty = fields.Selection(
        [('project_cancel', 'Project Cancel'),
         ('contract_cancel', 'Contract Cancel')], string='Penalty Type', required=True, )
    diff_penalty = fields.Boolean(string='Different Penalty')
    last_payment = fields.Selection([('first', 'First'), ('second ', 'Second'), ('final', 'Final')],
                                    string='Late Payment')
    cause_of_delay = fields.Char(string='Cause of Delay')
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage')
    amount = fields.Float(string='Amount')
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage')
    amount_client = fields.Float(string='Amount')


    days_needed_to_paid = fields.Integer(string='Days Needed to be Paid')
    days_delayed = fields.Integer(string='Days Delayed')

    note = fields.Html(string='Description')

    last_payment_method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Late Payment Method',)
    last_payment_interest = fields.Float(string='Late Payment Interest')
    delay_method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Delay Method',)
    delay_interest = fields.Float(string='Delay Interest')
    responsible = fields.Selection([('client', 'Client'), ('contractor', 'Contractor')], string='Responsible')
    
    # @api.constrains('penalty', 'days_needed_to_paid', 'amount')
    # def constrains_penalty(self):
    #     for res in self:
    #         if res.penalty in ['last_payment', 'project_delay']:
    #             if res.amount != 0:
    #                 if res.days_needed_to_paid <= 0:
    #                     raise UserError(_('The days needed to be paid cannot be 0. Please set the days the amount needed to be paid'))
    #                 elif res.amount <= 0:
    #                     raise UserError(_('The amount needed to be paid cannot be 0. Please set the amount needed to be paid'))
