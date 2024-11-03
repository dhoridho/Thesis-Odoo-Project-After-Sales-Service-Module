from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime

class RevenueForecastReport(models.TransientModel):
    _name = 'revenue.forecast.report'
    _description = 'Revenue FOrecast Report'
    
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    property_ids = fields.Many2many(comodel_name='product.product', string='Property', required=True, domain=[('is_property', '=', True)])
    
    def get_pdf_report(self):
        if self.start_date > self.end_date:
            raise UserError(_('Start Date should be less than End Date'))
        date_start = datetime.strftime(self.start_date, '%Y-%m-%d')
        date_end = datetime.strftime(self.end_date, '%Y-%m-%d')
        invoice_ids = self.env['account.move'].search([('partner_id.partner_type','in',['renter','purchaser']), ('invoice_date', '<=', date_end), ('invoice_date', '>=',date_start)])
        if not invoice_ids:
            raise UserError(_("No Invoices are available in this period."))
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'user_id': self.user_id.id,
                'invoice_ids': invoice_ids.ids,
                    }
                }
        return self.env.ref('equip3_property_report.print_revenue_forecast_report_action').report_action(self, data=data)

    def get_excel_report(self):
        return {
        'type': 'ir.actions.act_url', 
        'url': f'/property/property_wizard?id={self.id}&start={self.start_date}&end={self.end_date}',
        'target': 'new',
        }

    