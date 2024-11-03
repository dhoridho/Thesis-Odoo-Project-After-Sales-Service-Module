from odoo import fields, models, api, _
from datetime import datetime, timedelta, date

class VariationOrderLine(models.Model):
    _name = 'variation.order.line'
    _description = 'Variation Order External'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one('project.project', string="Project")
    contract_amount = fields.Float('Contract Amount')
    down_payment = fields.Float('Down Payment')
    dp_amount = fields.Float(string="Down Payment Amount")
    retention1 = fields.Float('Retention 1 (%)')
    retention1_amount = fields.Float(string="Retention 1 Amount")
    retention1_date = fields.Date('Retention 1 Date')
    retention_term_1 = fields.Many2one(
        'retention.term', string='Retention 1 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")  
    retention2 = fields.Float('Retention 2 (%)')
    retention2_amount = fields.Float(string="Retention 2 Amount")
    retention2_date = fields.Date('Retention 2 Date')
    retention_term_2 = fields.Many2one(
        'retention.term', string='Retention 2 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")  
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('active', '=', True)])
    payment_term = fields.Many2one('account.payment.term', 'Payment Term')
    vo_payment_type = fields.Selection([
                    ('join', 'Join Payment'),
                    ('split', 'Split Payment')
                    ], string="Payment Method")
    dp_method = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Down Payment Method", default='per')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company, readonly=True)
    

    @api.depends('project_id.variation_order_ids', 'project_id.variation_order_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_id.variation_order_ids:
                no += 1
                l.sr_no = no

class VariationOrderInternalLine(models.Model):
    _name = 'variation.order.internal.line'
    _description = 'Variation Order Internal'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=1) 
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_id = fields.Many2one('project.project', string="Project")
    approved_date = fields.Datetime('Approved Date')
    contract_amount = fields.Float('Contract Amount')

    @api.depends('project_id.variation_order_internal_ids', 'project_id.variation_order_internal_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_id.variation_order_internal_ids:
                no += 1
                l.sr_no = no
