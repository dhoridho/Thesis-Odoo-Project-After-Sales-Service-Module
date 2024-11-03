from odoo import api, fields, models
from datetime import datetime

class HrOutsourceAnalysis(models.Model):
    _name = 'hr.outsource.analysis'
    _description="HR Outsource Analysis"

    application_id = fields.Many2one('hr.applicant', string="Application")
    name = fields.Char("Subject / Application Name")
    partner_name = fields.Char("Applicant's Name")
    applicant_id = fields.Char("Applicant's ID")
    user_id = fields.Many2one('res.users', string="Recruiter")
    job_id = fields.Many2one('hr.job', string="Applied Job")
    department_id = fields.Many2one('hr.department', string="Department")
    work_location_id = fields.Many2one('work.location.object', string="Work Location")
    company_id = fields.Many2one('res.company', string="Company")
    outsource_id = fields.Many2one('hr.recruitment.outsource.master', string="Outsource")
    stage_id = fields.Many2one('hr.recruitment.stage', string="Stages")
    stage_replace_id = fields.Many2one('job.stage.line', string="Stage", domain="[('job_id','=',job_id)]")
    rate = fields.Float("Rate")
    timestamp = fields.Datetime("Timestamp", default=fields.datetime.now())
    timestamp_date = fields.Date("Timestamp Date", default=fields.Date.today())
    timestamp_month = fields.Char("Timestamp Month", compute='_get_timestamp_month_year', store=True)
    timestamp_year = fields.Char("Timestamp Year", compute='_get_timestamp_month_year', store=True)
    rate_by_aplicant_date = fields.Float("Rate by Applicant Date")
    aplicant_create_date = fields.Date("Aplicant Create Date")
    aplicant_create_date_month = fields.Char("Aplicant Create Date Month", compute='_get_aplicant_create_date_month_year', store=True)
    aplicant_create_date_year = fields.Char("Aplicant Create Date Year", compute='_get_aplicant_create_date_month_year', store=True)

    @api.depends('timestamp_date')
    def _get_timestamp_month_year(self):
        for rec in self:
            if rec.timestamp_date:
                timestamp_date = datetime.strptime(str(rec.timestamp_date),"%Y-%m-%d")
                rec.timestamp_month = timestamp_date.month
                rec.timestamp_year = timestamp_date.year

    @api.depends('aplicant_create_date')
    def _get_aplicant_create_date_month_year(self):
        for rec in self:
            if rec.aplicant_create_date:
                aplicant_create_date = datetime.strptime(str(rec.aplicant_create_date),"%Y-%m-%d")
                rec.aplicant_create_date_month = aplicant_create_date.month
                rec.aplicant_create_date_year = aplicant_create_date.year

    @api.onchange('application_id')
    def onchange_application_id(self):
        for rec in self:
            if rec.application_id:
                rec.name = rec.application_id.name
                rec.partner_name = rec.application_id.partner_name
                rec.applicant_id = rec.application_id.applicant_id
                rec.user_id = rec.application_id.user_id.id
                rec.job_id = rec.application_id.job_id.id
                rec.department_id = rec.application_id.department_id.id
                if rec.application_id.work_location_id:
                    rec.work_location_id = rec.application_id.work_location_id.id
                else:
                    rec.work_location_id = False
                rec.company_id = rec.application_id.company_id.id
                if rec.application_id.outsource_id:
                    rec.outsource_id = rec.application_id.outsource_id.id
                else:
                    rec.outsource_id = False
                rec.stage_id = rec.application_id.stage_id.id
                rec.stage_replace_id = rec.application_id.stage_replace_id.id
                rec.aplicant_create_date = rec.application_id.aplicant_create_date
    
    def get_rate(self):
        all_data = self.env['hr.outsource.analysis'].search([])
        if all_data:
            for rec in all_data:
                rec.rate = 0
                if not rec.stage_id.is_first_stage:
                    other_data = self.env['hr.outsource.analysis'].search([('id','!=',rec.id),('job_id','=',rec.job_id.id)])
                    other_data_filter = other_data.filtered(lambda r: r.stage_replace_id.sequence < rec.stage_replace_id.sequence).sorted(key=lambda r: r.stage_replace_id.sequence, reverse=False)[-1:]
                    if rec.outsource_id:
                        stage_before = other_data_filter.stage_replace_id.id if other_data_filter else False
                        other_data_stage_before = self.env['hr.outsource.analysis'].search([('id','!=',rec.id),('job_id','=',rec.job_id.id),('outsource_id','=',rec.outsource_id.id),('timestamp_month','=',rec.timestamp_month),('timestamp_year','=',rec.timestamp_year),('stage_replace_id','=',stage_before)])
                        count_data = len(other_data_stage_before)
                        rec.rate = ((1/count_data) * 100) / 100 if count_data else 0
                    else:
                        stage_before = other_data_filter.stage_replace_id.id if other_data_filter else False
                        other_data_stage_before = self.env['hr.outsource.analysis'].search([('id','!=',rec.id),('job_id','=',rec.job_id.id),('timestamp_month','=',rec.timestamp_month),('timestamp_year','=',rec.timestamp_year),('stage_replace_id','=',stage_before)])
                        count_data = len(other_data_stage_before)
                        rec.rate = ((1/count_data) * 100) / 100 if count_data else 0
    
    def get_rate_by_applicant_date(self):
        all_data = self.env['hr.outsource.analysis'].search([])
        if all_data:
            for rec in all_data:
                rec.rate_by_aplicant_date = 0
                if not rec.stage_id.is_first_stage:
                    other_data = self.env['hr.outsource.analysis'].search([('id','!=',rec.id),('job_id','=',rec.job_id.id)])
                    other_data_filter = other_data.filtered(lambda r: r.stage_replace_id.sequence < rec.stage_replace_id.sequence).sorted(key=lambda r: r.stage_replace_id.sequence, reverse=False)[-1:]
                    if rec.outsource_id:
                        stage_before = other_data_filter.stage_replace_id.id if other_data_filter else False
                        other_data_stage_before = self.env['hr.outsource.analysis'].search([('id','!=',rec.id),('job_id','=',rec.job_id.id),('outsource_id','=',rec.outsource_id.id),('aplicant_create_date_month','=',rec.aplicant_create_date_month),('aplicant_create_date_year','=',rec.aplicant_create_date_year),('stage_replace_id','=',stage_before)])
                        count_data = len(other_data_stage_before)
                        rec.rate_by_aplicant_date = ((1/count_data) * 100) / 100 if count_data else 0
                    else:
                        stage_before = other_data_filter.stage_replace_id.id if other_data_filter else False
                        other_data_stage_before = self.env['hr.outsource.analysis'].search([('id','!=',rec.id),('job_id','=',rec.job_id.id),('aplicant_create_date_month','=',rec.aplicant_create_date_month),('aplicant_create_date_year','=',rec.aplicant_create_date_year),('stage_replace_id','=',stage_before)])
                        count_data = len(other_data_stage_before)
                        rec.rate_by_aplicant_date = ((1/count_data) * 100) / 100 if count_data else 0