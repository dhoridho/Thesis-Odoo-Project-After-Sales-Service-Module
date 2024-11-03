# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from lxml import etree

class HrExpenseCycle(models.Model):
    _name = 'hr.expense.cycle'
    _description = 'Hr Expense Cycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Years", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    start_period_based_on = fields.Selection([('start_date', 'Start Date'), ('end_date', 'End Date')],
                     'Period Based on', default='', required=True)
    year_ids = fields.One2many('hr.expense.cycle.line', 'year_id', string='Expense Cycle Line')
    reimbursement_date_after = fields.Integer("Reimbursement Date after")
    is_confirm = fields.Boolean("Is Confirmed", default=False)
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrExpenseCycle, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        
        if  self.env.user.has_group('hr_expense.group_hr_expense_user'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.constrains('name')
    def check_name(self):
        for record in self:
            if record.name:
                check_name = self.search([('name', '=', record.name), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("Years must be unique!")
    
    @api.onchange('start_date', 'end_date')
    def _onchange_date(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError("End Date must be greater than Start Date!")

    def expense_confirm(self):
        expense_line = []
        for rec in self:
            rec.is_confirm = True
            rec.year_ids.unlink()
            start_date = datetime.strptime(str(rec.start_date), "%Y-%m-%d")
            ends_date = datetime.strptime(str(rec.end_date), "%Y-%m-%d")
            while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
                end_date = start_date + relativedelta(months=+1, days=-1)

                if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                    end_date = ends_date

                if rec.start_period_based_on == 'start_date':
                    year_date = start_date.strftime("%Y")
                    month_date = start_date.strftime("%B")
                    month_num = start_date.strftime("%m")
                elif rec.start_period_based_on == 'end_date':
                    year_date = end_date.strftime("%Y")
                    month_date = end_date.strftime("%B")
                    month_num = end_date.strftime("%m")
                
                expense_line.append((0, 0, {'year_id': self.id,
                                            'year': year_date,
                                            'month': month_date,
                                            'code': f"{month_num}/{year_date}",
                                            'cycle_start': start_date.strftime("%Y-%m-%d"),
                                            'cycle_end': end_date.strftime("%Y-%m-%d"),
                                            'reimbursement_date': end_date + timedelta(days=rec.reimbursement_date_after)
                                            }))
                start_date = start_date + relativedelta(months=+1)
            rec.year_ids = expense_line

    def name_get(self):
        return [(record.id, "%s" % (record.name)) for record in self]

    # _sql_constraints = [
    #     ('unique_hr_year_id', 'unique(hr_year_id)', 'Hr Year already taken by another Period'),
    # ]


class HrExpenseCycleLine(models.Model):
    _name = 'hr.expense.cycle.line'

    year_id = fields.Many2one('hr.expense.cycle', string='Expense Cycle', ondelete='cascade')
    year = fields.Char("Year")
    month = fields.Char("month")
    code = fields.Char("Cycle Code")
    cycle_start = fields.Date("Cycle Start")
    cycle_end = fields.Date("Cycle End")
    reimbursement_date = fields.Date("Reimbursement Date")

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % (rec.code)))
        return res


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = 'Register Payment'

    @api.depends('partner_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for wizard in self:
            wizard.get_bank_details()
            available_partner_bank_accounts = wizard.partner_id.bank_ids.filtered(lambda x: x.company_id in (False, wizard.company_id))
            if available_partner_bank_accounts:
                wizard.partner_bank_id = available_partner_bank_accounts[0]._origin
            else:
                wizard.partner_bank_id = False


    def get_bank_details(self):
        for pay in self:
            # if pay.partner_id.bank_ids:
            #     pay.partner_id.bank_ids = False
            exp_user_id = self.env['res.users'].search([('partner_id', '=', self.partner_id.id)], limit=1)
            if exp_user_id:
                exp_emp_id = self.env['hr.employee'].search([('user_id', '=', exp_user_id.id)], limit=1)
                if exp_emp_id:
                    exp_acc_rec = self.env['bank.account'].search([('employee_id', '=', exp_emp_id.id), ('is_used', '=', True)],
                                                                  limit=1)
                    if exp_acc_rec:
                        partner_bank = self.env['res.partner.bank'].search([('bank_id','=',exp_acc_rec.name.id),('acc_number','=',exp_acc_rec.acc_number),
                                                                            ('partner_id','=',self.partner_id.id),('company_id','=',self.company_id.id)],limit=1)
                        if not partner_bank:
                            self.env['res.partner.bank'].create({
                                'bank_id': exp_acc_rec.name.id,
                                'acc_number': exp_acc_rec.acc_number,
                                'partner_id': self.partner_id.id,
                                'company_id': self.company_id.id,
                            })

                    exp_acc_rec_false = self.env['bank.account'].search(
                        [('employee_id', '=', exp_emp_id.id), ('is_used', '=', False)])
                    if exp_acc_rec_false:
                        for acc_false in exp_acc_rec_false:
                            partner_bank = self.env['res.partner.bank'].search([('bank_id','=',acc_false.name.id),('acc_number','=',acc_false.acc_number),
                                                                            ('partner_id','=',self.partner_id.id),('company_id','=',self.company_id.id)],limit=1)
                            if not partner_bank:
                                self.env['res.partner.bank'].create({
                                    'bank_id': acc_false.name.id,
                                    'acc_number': acc_false.acc_number,
                                    'partner_id': self.partner_id.id,
                                    'company_id': self.company_id.id,
                                })