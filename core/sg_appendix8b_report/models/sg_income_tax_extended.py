from datetime import datetime

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from odoo.exceptions import ValidationError


class HRContractIncomeTax(models.Model):
    _inherit = 'hr.contract.income.tax'

    app_8b_income_tax = fields.One2many('appendix.8b.income.tax',
                                        'app8b_inc_tx', "Appendix 8B")


class Appendix8bIncomeTax(models.Model):
    _name = 'appendix.8b.income.tax'
    _description = "Appendix 8b report"

    @api.depends('moratorium_price', 'esow_plan', 'open_val_esop',
                 'tax_plan', 'no_of_share')
    def _calculate_eris(self):
        for rec in self:
            open_mar_val = 0.0
            eris_value = 0.0
            if rec.tax_plan == 'esop':
                if rec.moratorium_price != 0:
                    open_mar_val += rec.moratorium_price
                else:
                    open_mar_val += rec.open_val_esop
                eris_value = (open_mar_val - rec.open_val_esop
                              ) * rec.no_of_share
            if rec.tax_plan == 'esow':
                if rec.moratorium_price != 0:
                    open_mar_val += rec.moratorium_price
                else:
                    open_mar_val += rec.esow_plan
                eris_value = (open_mar_val - rec.esow_plan) * rec.no_of_share
            rec.eris_smes = eris_value
            rec.eris_all_corporation = eris_value
            rec.eris_start_ups = eris_value

    @api.depends('moratorium_price', 'open_val_esop', 'ex_price_esop',
                 'no_of_share', 'pay_under_esow', 'esow_plan', 'tax_plan')
    def _calculate_gross_amount(self):
        for rec in self:
            open_mar_val = 0.0
            secA_grss_amt = 0.0
            secB_grss_amt = 0.0
            secC_grss_amt = 0.0
            secD_grss_amt = 0.0
            if rec.tax_plan == 'esop':
                if rec.moratorium_price != 0:
                    open_mar_val += rec.moratorium_price
                else:
                    open_mar_val += rec.open_val_esop
                secA_grss_amt += (open_mar_val - rec.ex_price_esop
                                  ) * rec.no_of_share
                secB_grss_amt += (rec.open_val_esop - rec.ex_price_esop
                                  ) * rec.no_of_share
                secC_grss_amt += (rec.open_val_esop - rec.ex_price_esop
                                  ) * rec.no_of_share
                secD_grss_amt += (rec.open_val_esop - rec.ex_price_esop
                                  ) * rec.no_of_share
            if rec.tax_plan == 'esow':
                if rec.moratorium_price != 0:
                    open_mar_val += rec.moratorium_price
                else:
                    open_mar_val += rec.esow_plan
                secA_grss_amt += (open_mar_val - rec.pay_under_esow
                                  ) * rec.no_of_share
                secB_grss_amt += (rec.esow_plan - rec.pay_under_esow
                                  ) * rec.no_of_share
                secC_grss_amt += (rec.esow_plan - rec.pay_under_esow
                                  ) * rec.no_of_share
                secD_grss_amt += (rec.esow_plan - rec.pay_under_esow
                                  ) * rec.no_of_share
            rec.secA_grss_amt_qulfy_tx = secA_grss_amt
            rec.secB_grss_amt_qulfy_tx = secB_grss_amt
            rec.secC_grss_amt_qulfy_tx = secC_grss_amt
            rec.secD_grss_amt_qulfy_tx = secD_grss_amt

    app8b_inc_tx = fields.Many2one('hr.contract.income.tax', "Incometax")
    section = fields.Selection([('sectionA', 'SECTION A: EMPLOYEE EQUITY-BASED \
                                                REMUNERATION (EEBR) SCHEME'),
                                ('sectionB', 'SECTION B: EQUITY REMUNERATION \
                                                INCENTIVE SCHEME (ERIS) SMEs'),
                                ('sectionC', 'SECTION C: EQUITY REMUNERATION \
                                    INCENTIVE SCHEME (ERIS) ALL CORPORATIONS'),
                                ('sectionD', 'SECTION D: EQUITY REMUNERATION \
                                        INCENTIVE SCHEME (ERIS) START-UPs')],
                               default="sectionA", string="Section")
    tax_plan = fields.Selection([('esop', 'ESOP'), ('esow', 'ESOW')],
                                "Taxability Plan", default="esop")
    tax_plan_grant_date = fields.Date("Date of Grant")
    esop_date = fields.Date("Date of exercise of ESOP")
    esow_date = fields.Date("Date of vesting of ESOW")
    is_moratorium = fields.Boolean("Is Moratorium ?")
    moratorium_date = fields.Date("Moratorium Date")
    moratorium_price = fields.Float(
        "Open Market Value Per Share as at the Date of Moratorium",
        digits='Incometax'
    )
    ex_price_esop = fields.Float("Exercise Price of ESOP",
                                 digits='Incometax')
    pay_under_esow = fields.Float("Payable per Share under ESOW plan",
                                  digits='Incometax')
    open_val_esop = fields.Float(
        "Open Market Value Per share as at the Date of Grant of ESOP",
        digits='Incometax')
    esow_plan = fields.Float("ESOW Plan", digits='Incometax')
    no_of_share = fields.Float("Number of Shares Acquired",
                               digits='Incometax')
    eris_smes = fields.Float(compute="_calculate_eris", string="ERIS(SMEs)",
                             digits='Payroll')
    eris_all_corporation = fields.Float(compute='_calculate_eris',
                                        string="ERIS(All Corporations)",
                                        digits='Payroll')
    eris_start_ups = fields.Float(compute='_calculate_eris',
                                  string="ERIS(Start-ups)",
                                  digits='Payroll')
    secA_grss_amt_qulfy_tx = fields.Float(
        compute='_calculate_gross_amount',
        string="Gross Amount not Qualifying for Tax Exemption ($)",
        digits='Payroll')
    secB_grss_amt_qulfy_tx = fields.Float(
        compute='_calculate_gross_amount',
        string="Gross Amount not Qualifying for Tax Exemption ($)",
        digits='Payroll')
    secC_grss_amt_qulfy_tx = fields.Float(
        compute='_calculate_gross_amount',
        string="Gross Amount not Qualifying for Tax Exemption ($)",
        digits='Payroll')
    secD_grss_amt_qulfy_tx = fields.Float(
        compute='_calculate_gross_amount',
        string="Gross Amount not Qualifying for Tax Exemption ($)",
        digits='Payroll')

    @api.onchange('tax_plan')
    def onchange_tax_plan(self):
        for plan in self:
            if plan.tax_plan == 'esop':
                plan.esow_plan = plan.pay_under_esow = plan.esow_date = ''
            elif plan.tax_plan == 'esow':
                plan.esop_date = plan.ex_price_esop = plan.open_val_esop = ''

    @api.onchange('tax_plan', 'tax_plan_grant_date', 'section')
    def check_grant_date(self):
        for rec in self:
            grant_date = rec.tax_plan_grant_date
            if grant_date:
                if rec.section == 'sectionA':
                    today = datetime.today().date()
                    if grant_date > today:
                        raise ValidationError(
                            _("Grant date for Section A can not be future date!"))
                elif rec.section == 'sectionB':
                    if rec.tax_plan == 'esop':
                        secB_grant_start_date = datetime.strptime('2000-01-01',
                                                                  DSDF)
                        secB_grant_end_date = datetime.strptime('2013-12-31',
                                                                DSDF)
                        if grant_date < secB_grant_start_date.date() or \
                                grant_date > secB_grant_end_date.date():
                            raise ValidationError(
                                _("Grant date for Section B ESOP must be "
                                  "between 1 Jan 2000 TO 31 Dec 2013!"))
                    elif rec.tax_plan == 'esow':
                        secB_grant_start_date = datetime.strptime('2002-01-01',
                                                                  DSDF)
                        secB_grant_end_date = datetime.strptime('2013-12-31',
                                                                DSDF)
                        if grant_date < secB_grant_start_date.date() or \
                                grant_date > secB_grant_end_date.date():
                            raise ValidationError(
                                _("Grant date for Section B ESOW must be "
                                  "between 1 Jan 2002 TO 31 Dec 2013!"))
                elif rec.section == 'sectionC':
                    if rec.tax_plan == 'esop':
                        secC_grant_start_date = datetime.strptime('2001-04-01',
                                                                  DSDF)
                        secC_grant_end_date = datetime.strptime('2013-12-31',
                                                                DSDF)
                        if grant_date < secC_grant_start_date.date() or \
                                grant_date > secC_grant_end_date.date():
                            raise ValidationError(
                                _("Grant date for Section C ESOP must be "
                                  "between 1 Apr 2001 TO 31 Dec 2013!"))
                    elif rec.tax_plan == 'esow':
                        secC_grant_start_date = datetime.strptime('2002-01-01',
                                                                  DSDF)
                        secC_grant_end_date = datetime.strptime('2013-12-31',
                                                                DSDF)
                        if grant_date < secC_grant_start_date.date() or \
                                grant_date > secC_grant_end_date.date():
                            raise ValidationError(
                                _("Grant date for Section C ESOW must be "
                                  "between 1 Jan 2002 TO 31 Dec 2013!"))
                elif rec.section == 'sectionD':
                    secD_grant_start_date = datetime.strptime('2008-02-16',
                                                              DSDF)
                    secD_grant_end_date = datetime.strptime('2013-02-15',
                                                            DSDF)
                    if grant_date < secD_grant_start_date.date() or \
                            grant_date > secD_grant_end_date.date():
                        raise ValidationError(
                            _("Grant date for Section D must be between "
                              "16 Feb 2008 TO 15 Feb 2013!"))

    @api.onchange('esop_date', 'esow_date', 'section', 'tax_plan_grant_date',
                  'tax_plan')
    def _check_date(self):
        for data in self:
            if data.tax_plan_grant_date:
                grant_date = data.tax_plan_grant_date
                grant_year = grant_date.year
                income_year = data.app8b_inc_tx.end_date.year
                if data.tax_plan == 'esop':
                    if data.esop_date:
                        esop_date = data.esop_date
                        esop_year = esop_date.year
                        esop_end_date = datetime.strptime('2023-12-31',
                                                          '%Y-%m-%d')
                        if data.section == 'sectionA':
                            if esop_year >= income_year:
                                raise ValidationError(
                                    _("Date of exercise for ESOP is accepted "
                                      "up to previous income years!"))
                            elif grant_year == esop_year and \
                                    esop_date < grant_date:
                                raise ValidationError(
                                    _("Date of exercise for ESOP can not be "
                                      "later then Grant date!"))
                        elif data.section == 'sectionB':
                            if esop_year >= income_year:
                                raise ValidationError(
                                    _("Date of exercise for ESOP is accepted "
                                      "up to previous income years!"))
                            elif esop_year == grant_year:
                                if esop_date < grant_date or \
                                        esop_date > esop_end_date.date():
                                    raise ValidationError(
                                        _("Date of exercises for ESOP must "
                                          "be later then Grant date and "
                                          "before 31 Dec 2023!"))
                        elif data.section == 'sectionC':
                            if esop_year >= income_year:
                                raise ValidationError(
                                    _("Date of exercise for ESOP is accepted "
                                      "up to previous income years!"))
                            elif esop_year == grant_year:
                                if esop_date < grant_date or \
                                            esop_date > esop_end_date.date():
                                    raise ValidationError(
                                        _("Date of exercises for ESOP must be "
                                          "later then Grant date and before "
                                          "31 Dec 2023!"))
                        elif data.section == 'sectionD':
                            if esop_year >= income_year:
                                raise ValidationError(
                                    _("Date of exercise for ESOP is accepted "
                                      "up to previous income years!"))
                            elif esop_year == grant_year:
                                if esop_date < grant_date or \
                                        esop_date > esop_end_date.date():
                                    raise ValidationError(
                                        _("Date of exercises for ESOP must be "
                                          "later then Grant date and before "
                                          "31 Dec 2023!"))
                elif data.tax_plan == 'esow':
                    if data.esow_date:
                        esow_date = data.esow_date
                        esow_year = esow_date.year
                        esow_end_date = datetime.strptime('2023-12-31',
                                                          '%Y-%m-%d')
                        if data.section == 'sectionA':
                            if esow_year >= income_year:
                                raise ValidationError(
                                    _("Date of exercise for ESOW is accepted "
                                      "up to previous income years!"))
                            elif esow_year == grant_year and \
                                    esow_date < grant_date:
                                raise ValidationError(
                                    _("Date of exercise for ESOW can not be "
                                      "later then Grant date!"))
                        elif data.section == 'sectionB':
                            if esow_year >= income_year:
                                    raise ValidationError(
                                        _("Date of exercise for ESOW is "
                                          "accepted up to previous "
                                          "income years!"))
                            elif esow_year == grant_year:
                                if esow_date < grant_date or \
                                            esow_date > esow_end_date.date():
                                    raise ValidationError(
                                        _("Date of exercises for ESOW must be "
                                          "later then Grant date and before "
                                          "31 Dec 2023!"))
                        elif data.section == 'sectionC':
                            if esow_year >= income_year:
                                    raise ValidationError(
                                        _("Date of exercise for ESOW is "
                                          "accepted up to previous "
                                          "income years!"))
                            elif esow_year == grant_year:
                                if esow_date < grant_date or \
                                            esow_date > esow_end_date.date():
                                    raise ValidationError(
                                        _("Date of exercises for ESOW must be "
                                          "later then Grant date and before "
                                          "31 Dec 2023!"))
                        elif data.section == 'sectionD':
                            if esow_year >= income_year:
                                    raise ValidationError(
                                        _("Date of exercise for ESOW is "
                                          "accepted up to previous "
                                          "income years!"))
                            elif esow_year == grant_year:
                                if esow_date < grant_date or \
                                        esow_date > esow_end_date.date():
                                    raise ValidationError(
                                        _("Date of exercises for ESOW must be "
                                          "later then Grant date and before "
                                          "31 Dec 2023!"))
