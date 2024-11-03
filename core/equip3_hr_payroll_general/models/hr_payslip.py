from odoo import models,fields,api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period', domain="[('state','=','open')]")
    month = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]")
    month_name = fields.Char('Month Name', readonly=True)
    year = fields.Char('Year', readonly=True)
    payslip_report_date = fields.Date(string='Payslip Report Date', readonly=True)
    
    
    
    
    @api.onchange('payslip_period_id')
    def _onchange_payslip_period_id(self):
        for res in self:
            if res.payslip_period_id:
                res.date_from = False
                res.date_to = False

    @api.onchange('month')
    def _onchange_month(self):
        for res in self:
            if res.payslip_period_id:
                if res.month:
                    period_line_obj = self.env['hr.payslip.period.line'].search(
                        [('id', '=', res.month.id)], limit=1)
                    if period_line_obj:
                        for rec in period_line_obj:
                            res.date_from = rec.start_date
                            res.date_to = rec.end_date
                            res.month_name = res.month.month
                            res.year = res.month.year
                        if res.payslip_period_id.start_period_based_on == 'start_date':
                            res.payslip_report_date = res.date_from
                        elif res.payslip_period_id.start_period_based_on == 'end_date':
                            res.payslip_report_date = res.date_to
                    else:
                        res.date_from = False
                        res.date_to = False
                        res.month_name = False
                        res.year = False
    