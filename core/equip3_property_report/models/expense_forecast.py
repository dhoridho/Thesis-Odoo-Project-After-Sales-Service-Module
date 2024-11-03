from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime

class RevenueForecastReport(models.TransientModel):
    _name = 'expense.forecast.report'
    _description = 'Revenue FOrecast Report'
    
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    
    def get_pdf_report(self):
        if self.start_date > self.end_date:
            raise UserError(_('Start Date should be less than End Date'))
        mwo = self.env['maintenance.work.order'].search([('property_id', '!=', False), ('startdate', '>=', self.start_date), ('startdate', '<=', self.end_date)])
        mro = self.env['maintenance.repair.order'].search([('property_id', '!=', False), ('date_start', '>=', self.start_date), ('date_start', '<=', self.end_date)])
        agreement = self.env['agreement'].search([('property_id', '!=', False)])
        expense = self.env['agreement.expense.plan'].search([('agreement_id', 'in', agreement.ids)])
        bills = self.env['account.move'].search([('move_type','=','in_invoice'), ('expense_plan_id', 'in', expense.ids), ('invoice_date','>=',self.start_date), ('invoice_date','<=',self.end_date)])
        
        if not mwo and not mro:
            raise UserError(_('No Work Order or Repair Order found for this date range'))
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'user_id': self.user_id.id,
                'mwo': mwo.ids,
                'mro': mro.ids,
                'expense': expense.ids,
                'bills': bills.ids,
                }
            }
        return self.env.ref('equip3_property_report.print_expense_forecast_report_action').report_action(self, data=data)

    
