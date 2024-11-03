from odoo import _, api, fields, models


class JobEstimateReport(models.TransientModel):
    _name = 'job.estimate.report'
    _description = 'BOQ Report Wizard'

    print_option = fields.Selection(string='Type', selection=[('excel', 'Excel'), ('pdf', 'PDF'), ], default='excel')
    print_level_option = fields.Selection(string='Level', selection=[('2_level', "2 Levels (Project Scope, Section)"), (
        '3_level', "3 Levels (Project Scope, Section, Product)")], default='2_level')
    job_estimate_id = fields.Many2one('job.estimate', string='job_estimate')

    def print_job_estimate(self):
        if self.print_option == 'excel':
            return {
                'type': 'ir.actions.act_url',
                'url': '/equip3_construction_sales_operation/job_estimate_excel_report/%s' % (self.id),
                'target': 'self',
            }
        else:
            self.ensure_one()
            job_estimate_id = self.job_estimate_id
            data_rows = job_estimate_id.report_data2array(job_estimate_id.get_report_data(self.print_level_option))

            datas = {
                'ids': self.ids,
                'model': 'job.estimate',
                'job_estimate_id': self.job_estimate_id.id,
                'data_rows': data_rows,
                'print_level_option': self.print_level_option,
            }
            report_id = self.env.ref(
                'equip3_construction_sales_operation.action_report_construction_job_estimate')
            report_id.write({'name': "BOQ - " + job_estimate_id.number or ''})
            return report_id.report_action(self, data=datas)
