from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ReportMenu(models.Model):
    _name = 'menu.accounting.c'
    _description = 'menu.accounting.c'

    name = fields.Char(string='Name Of Person')
    sctp_no = fields.Char(string='SCTP Membership')
    contact_person = fields.Char(string='Contact Person')
    designation = fields.Char(string='Designation')
    email_address = fields.Char(string='Email Address')
    mobile = fields.Char(string='Mobile', default='', help="Enter a valid phone number (10-12 digits)")
    Office = fields.Char(string='Office', default='')
    sctp_radio = fields.Selection([('option1', 'Yes'), ('option2', 'No'), ('option3', 'NA')])
    audited_radio = fields.Selection([('option1', 'Audited'), ('option2', 'Unaudited')])
    radio_button_a = fields.Selection([('option1', 'Yes'), ('option2', 'No')])
    radio_button_b = fields.Selection([('option1', 'Yes'), ('option2', 'No')])
    radio_button_c = fields.Selection([('option1', 'Yes'), ('option2', 'No')])
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    trade_business_income = fields.Float()
    trade_business_lose = fields.Float()
    other_income_not_falling_under_items_1a = fields.Float()
    other_income_not_falling_under_items_1e = fields.Float()
    total_income_before_donation = fields.Float()
    total_loss_before_donation = fields.Float()
    chargeable_income = fields.Float()
    loss_claimed_from_transferor_company_from = fields.Float()
    loss_claimed_from_transferor_company_to = fields.Float()
    chargeable_income_after_group_relief_from = fields.Float()
    chargeable_income_after_group_relief_to = fields.Float()
    tax_to_be_remitted_under_section_92_1 = fields.Float()
    tax_to_be_remitted_under_section_92_2 = fields.Float()
    unutilisted_donation_normal_rate1 = fields.Float(readonly=True)
    unutilisted_donation_normal_rate2 = fields.Float(readonly=True)
    company_declaration_unutilisted_donation_normal_rate1 = fields.Float()
    company_declaration_unutilisted_donation_normal_rate2 = fields.Float()
    unutilisted_donation_concessionary_rate1 = fields.Float(readonly=True)
    unutilisted_donation_concessionary_rate2 = fields.Float(readonly=True)
    company_declaration_unutilisted_donation_concessionary_rate1 = fields.Float()
    company_declaration_unutilisted_donation_concessionary_rate2 = fields.Float()
    current_year_donation_1 = fields.Float(readonly=True)
    current_year_donation_2 = fields.Float(readonly=True)
    company_declaration_current_year_donation_1 = fields.Float()
    company_declaration_current_year_donation_2 = fields.Float()
    foreign_ids = fields.One2many('foreign.income.received', 'form_c_id', string='Foreign Income Received')
    due_date = fields.Date(string='Due Date')
    assessment_year =fields.Char(string='Assessment Year', readonly=True, default=lambda self: fields.Date.today().year)
    radio_button_string_the_company = fields.Selection([('option1', 'Yes'), ('option2', 'No')])
    radio_button_particular = fields.Selection([('option1', 'Yes'), ('option2', 'No')])
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    @api.constrains('foreign_ids')
    def _check_foreign_ids(self):
        for rec in self:
            if len(rec.foreign_ids) > 6:
                raise ValidationError("You can add only 6 foreign income received.")

    @api.onchange('company_declaration_unutilisted_donation_normal_rate1')
    def _onchange_company_declaration_unutilisted_donation_normal_rate1(self):
        if self.company_declaration_unutilisted_donation_normal_rate1:
            self.unutilisted_donation_normal_rate1 = self.company_declaration_unutilisted_donation_normal_rate1

    @api.onchange('company_declaration_unutilisted_donation_normal_rate2')
    def _onchange_company_declaration_unutilisted_donation_normal_rate2(self):
        if self.company_declaration_unutilisted_donation_normal_rate2:
            self.unutilisted_donation_normal_rate2 = self.company_declaration_unutilisted_donation_normal_rate2

    @api.onchange('company_declaration_unutilisted_donation_concessionary_rate1')
    def _onchange_company_declaration_unutilisted_donation_concessionary_rate1(self):
        if self.company_declaration_unutilisted_donation_concessionary_rate1:
            self.unutilisted_donation_concessionary_rate1 = self.company_declaration_unutilisted_donation_concessionary_rate1

    @api.onchange('company_declaration_unutilisted_donation_concessionary_rate2')
    def _onchange_company_declaration_unutilisted_donation_concessionary_rate2(self):
        if self.company_declaration_unutilisted_donation_concessionary_rate2:
            self.unutilisted_donation_concessionary_rate2 = self.company_declaration_unutilisted_donation_concessionary_rate2

    @api.onchange('company_declaration_current_year_donation_1')
    def _onchange_company_declaration_current_year_donation_1(self):
        if self.company_declaration_current_year_donation_1:
            self.current_year_donation_1 = self.company_declaration_current_year_donation_1

    @api.onchange('company_declaration_current_year_donation_2')
    def _onchange_company_declaration_current_year_donation_2(self):
        if self.company_declaration_current_year_donation_2:
            self.current_year_donation_2 = self.company_declaration_current_year_donation_2


class ForeignIncomeReceived(models.Model):
    _name = 'foreign.income.received'
    _description = 'foreign.income.received'

    nature_of_income = fields.Selection(selection=[('passive_income', 'Passive Income'),
                                                   ('active_income', 'Active Income')])
    country = fields.Many2one('res.country', string='Country/Territory')
    amount_1 = fields.Float(string='Amount')
    amount_2 = fields.Float(string='Amount')
    form_c_id = fields.Many2one('menu.accounting.c', string='Form C')

