from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class ProjecProjectSubcon(models.Model):
    _inherit = 'project.project'

    contract_subcon_ids = fields.One2many('contract.subcon.const', 'project_id')


class ContractSubcon(models.Model):
    _name = 'contract.subcon.const'
    _description = 'Contract Subcon'
    _order = 'sequence'

    partner_id = fields.Many2one('res.partner', string='Vendor')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company, readonly=True)
    name = fields.Many2one('purchase.order', string='Contract Subcon')
    order_date = fields.Datetime(string='Order Date')
    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one('project.project', string="Project")

    # Total All Contract
    contract_amount_subcon = fields.Float(string='Contract Amount', compute="_compute_contract_amount_subcon")
    dp_amount_subcon = fields.Float(string="Down Payment", compute="_compute_dp_amount_subcon")
    retention1_amount_subcon = fields.Float(string="Retention 1", compute="_compute_retention1_amount_subcon")
    retention2_amount_subcon = fields.Float(string="Retention 2", compute="_compute_retention2_amount_subcon")
     
    # main contract
    subcon_contract_amount = fields.Float(string='Contract Amount')
    subcon_dp_method = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Down Payment Method", default='per')
    subcon_down_payment = fields.Float('Down Payment')
    subcon_dp_amount = fields.Float(string="Down Payment Amount", compute="_compute_main_downpayment_subcon")
    subcon_retention1 = fields.Float('Retention 1 (%)')
    subcon_retention1_amount = fields.Float(string="Retention 1 Amount", compute="_compute_main_retention1_subcon")
    subcon_retention1_date = fields.Date('Retention 1 Date')
    subcon_retention2 = fields.Float('Retention 2 (%)')
    subcon_retention2_amount = fields.Float(string="Retention 2 Amount", compute="_compute_main_retention2_subcon")
    subcon_retention2_date = fields.Date('Retention 2 Date')
    subcon_tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('active', '=', True)])
    subcon_payment_term = fields.Many2one('account.payment.term', 'Payment Term')
    subcon_retention_term_1 = fields.Many2one(
        'retention.term', string='Retention 1 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    subcon_retention_term_2 = fields.Many2one(
        'retention.term', string='Retention 2 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    # Project Progress
    subcon_outstanding_limit = fields.Float(string='Outstanding Limit')
    subcon_status_progress = fields.Float(string='Status Progress')

    variation_subcon_ids = fields.One2many('variation.subcon.line', 'contract_id')

    @api.depends('project_id.contract_subcon_ids', 'project_id.contract_subcon_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_id.contract_subcon_ids:
                no += 1
                l.sr_no = no

    @api.depends('subcon_dp_method','subcon_down_payment', 'subcon_contract_amount')
    def _compute_main_downpayment_subcon(self):
        for res in self:
            if res.subcon_dp_method == 'per':
                res.subcon_dp_amount = res.subcon_contract_amount * (res.subcon_down_payment / 100)
            elif res.subcon_dp_method == 'fix':
                res.subcon_dp_amount = res.subcon_down_payment
            else:
                res.subcon_dp_amount = 0

    @api.depends('subcon_retention1', 'subcon_contract_amount')
    def _compute_main_retention1_subcon(self):
        for res in self:
            res.subcon_retention1_amount = res.subcon_contract_amount * (res.subcon_retention1 / 100)

    @api.depends('subcon_retention2', 'subcon_contract_amount')
    def _compute_main_retention2_subcon(self):
        for res in self:
            res.subcon_retention2_amount = res.subcon_contract_amount * (res.subcon_retention2 / 100)

    @api.depends('variation_subcon_ids.contract_amount','subcon_contract_amount')
    def _compute_contract_amount_subcon(self):
        total1 = 0
        for res1 in self:
            total1 = sum(res1.variation_subcon_ids.mapped('contract_amount'))
            res1.contract_amount_subcon = total1 + res1.subcon_contract_amount
        return total1

    @api.depends('variation_subcon_ids.dp_amount','subcon_dp_amount')
    def _compute_dp_amount_subcon(self):
        total2 = 0
        for res2 in self:
            total2 = sum(res2.variation_subcon_ids.mapped('dp_amount'))
            res2.dp_amount_subcon = total2 + res2.subcon_dp_amount
        return total2

    @api.depends('variation_subcon_ids.retention1_amount','subcon_retention1_amount')
    def _compute_retention1_amount_subcon(self):
        total3 = 0
        for res3 in self:
            total3 = sum(res3.variation_subcon_ids.mapped('retention1_amount'))
            res3.retention1_amount_subcon = total3 + res3.subcon_retention1_amount
        return total3

    @api.depends('variation_subcon_ids.retention2_amount', 'subcon_retention2_amount')
    def _compute_retention2_amount_subcon(self):
        total4 = 0
        for res4 in self:
            total4 = sum(res4.variation_subcon_ids.mapped('retention2_amount'))
            res4.retention2_amount_subcon = total4 + res4.subcon_retention2_amount
        return total4


class VariationOrderLineSubcon(models.Model):
    _name = 'variation.subcon.line'
    _description = 'Variation Order Subcon'
    _order = 'sequence'

    contract_id = fields.Many2one('contract.subcon.const', string='Contract Subcon', ondelete="cascade")
    company_id = fields.Many2one(related='contract_id.company_id', string='Company')
    name = fields.Many2one('purchase.order', string='Contract Subcon')
    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one(related='contract_id.project_id', string="Project")
    contract_amount = fields.Float('Contract Amount')
    down_payment = fields.Float('Down Payment')
    dp_amount = fields.Float(string="Down Payment Amount")
    retention1 = fields.Float('Retention 1 (%)')
    retention1_amount = fields.Float(string="Retention 1 Amount")
    retention1_date = fields.Date('Retention 1 Date')
    retention2 = fields.Float('Retention 2 (%)')
    retention2_amount = fields.Float(string="Retention 2 Amount")
    retention2_date = fields.Date('Retention 2 Date')
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('active', '=', True)])
    payment_term = fields.Many2one('account.payment.term', 'Payment Term')
    vo_payment_type = fields.Selection([
                    ('join_payment', 'Join Payment'),
                    ('split_payment', 'Split Payment')
                    ], string="Payment Method")
    dp_method = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Down Payment Method", default='per')
    order_date = fields.Datetime(string='Order Date')
    partner_id = fields.Many2one(related='contract_id.partner_id', string='Vendor')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company, readonly=True)
    retention_term_1 = fields.Many2one(
        'retention.term', string='Retention 1 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    retention_term_2 = fields.Many2one(
        'retention.term', string='Retention 2 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('contract_id.variation_subcon_ids', 'contract_id.variation_subcon_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.contract_id.variation_subcon_ids:
                no += 1
                l.sr_no = no

