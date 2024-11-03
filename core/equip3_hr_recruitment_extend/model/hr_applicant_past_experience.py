from odoo import fields,models,api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class HrApplicantPastExperience(models.Model):
    _name = 'hr.applicant.past.experience'
    start_date = fields.Date()
    end_date = fields.Date()
    company_name = fields.Char()
    position = fields.Char()
    reason_for_leaving = fields.Char()
    salary = fields.Float()
    company_telephone_number = fields.Char()
    applicant_id = fields.Many2one('hr.applicant')
    is_currently_work_here = fields.Boolean("Currently Work Here")
    job_descriptions = fields.Char("Job Descriptions")
    total_working_experience = fields.Char(compute='_compute_total_working_experience', string='Working Experience', store=True)
    # total_working_experience_years = fields.Char(compute='_compute_total_working_experience_years', string='Total Working Experience Years', store=True)
    total_working_only_years = fields.Integer(compute='_total_compute_years_months_days', invisible=True, store=False)


    def _total_compute_years_months_days(self):
        for record in self:
            if record.start_date and record.end_date:
                start_date_str = record.start_date.strftime('%Y-%m-%d')
                end_date_str = record.end_date.strftime('%Y-%m-%d')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                delta = relativedelta(end_date, start_date)
                years = delta.years
                months = delta.months 
                days = delta.days
                total_days = years * 365 + months * 31 + days 
                record.total_working_only_years = total_days
            else:
                record.total_working_only_years = 0
    
    @api.depends('start_date', 'end_date', 'is_currently_work_here')
    def _compute_total_working_experience(self):
        for record in self:
            start_date = record.start_date
            end_date = record.end_date
            experience_str = ""
    
            if record.is_currently_work_here:
                end_date = datetime.now().date()
    
            if start_date and end_date:
                delta = relativedelta(end_date, start_date)
                total_years = delta.years
                total_months = delta.months
                total_days = delta.days
    
                if total_years > 0:
                    experience_str += f"{total_years} year{'s' if total_years > 1 else ''} "
                if total_months > 0:
                    experience_str += f"{total_months} month{'s' if total_months > 1 else ''} "
                if total_days > 0:
                    experience_str += f"{total_days} day{'s' if total_days > 1 else ''} "
    
                record.total_working_experience = experience_str.strip()
            else:
                record.total_working_experience = ""

 

    # @api.depends('start_date', 'end_date', 'is_currently_work_here')
    # def _compute_total_working_experience(self):
    #     for record in self:
    #         start_date = record.start_date
    #         end_date = record.end_date
    #         if record.is_currently_work_here:
    #             end_date = datetime.now().date()
    #         if start_date and end_date:
    #             delta = relativedelta(end_date, start_date)
    #             total_years = delta.years
    #             total_months = delta.months
    #             total_days = delta.days
    #             if total_years > 0:
    #                 experience_str = f"{total_years} year{'s' if total_years > 1 else ''}"
    #             elif total_months > 0:
    #                 experience_str = f"{total_months} month{'s' if total_months > 1 else ''}"
    #             else:
    #                 experience_str = f"{total_days} day{'s' if total_days > 1 else ''}"
    #             record.total_working_experience = experience_str
    #         else:
    #             record.total_working_experience = ""


    # def _compute_total_working_experience(self):
    #     for record in self:
    #         if record.start_date and record.end_date:
    #             start_date_str = record.start_date.strftime('%Y-%m-%d')
    #             end_date_str = record.end_date.strftime('%Y-%m-%d')
    #             start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    #             end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    #             delta = relativedelta(end_date, start_date)
    #             years = delta.years
    #             months = delta.months
    #             days = delta.days
    #             years_str = '{} Year{}'.format(years, 's' if years > 1 else '')
    #             months_str = '{} Month{}'.format(months, 's' if months > 1 else '')
    #             days_str = '{} Day{}'.format(days, 's' if days > 1 else '')
    #             parts = []
    #             if years > 0:
    #                 parts.append(years_str)
    #             if months > 0:
    #                 parts.append(months_str)
    #             if days > 0:
    #                 parts.append(days_str)
    #             record.total_working_experience = ' '.join(parts)
    #         else:
    #             record.total_working_experience = '0 year'

    # def _compute_total_working_experience_years(self):
    #     for record in self:
    #         total_exp = record.total_working_experience
    #         years = total_exp.split(' ')[0]
    #         record.total_working_experience_years = '{} Years of working experience'.format(years)

