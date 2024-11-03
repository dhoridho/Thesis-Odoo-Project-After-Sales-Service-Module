from odoo import models, fields, tools, api


class SurveyMbtiReporting(models.Model):
    _name = 'mbti.reporting'
    _description = "MBTI Reporting"
    _auto = False

    personality = fields.Char("Personality")
    applicant_id = fields.Many2one('hr.applicant', string="Applicant")
    applicant_name = fields.Char(string='Applicant Name')
    create_on = fields.Datetime('Create On')
    deadline = fields.Datetime('Deadline')


    def _query(self):
        select = """
                SELECT
                    ROW_NUMBER () over() AS id,
                    sui.mbti_result AS personality,
                    sui.applicant_id AS applicant_id,
                    hra.partner_name AS applicant_name,
                    sui.create_date AS created_on,
                    sui.deadline AS deadline
                    FROM survey_user_input sui
                    LEFT JOIN hr_applicant hra ON (sui.applicant_id = hra.id)
                WHERE
                    sui.survey_type = 'MBTI' AND
                    sui.mbti_result IS NOT NULL
                """
        return select
    
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("CREATE OR REPLACE VIEW %s AS (%s)" % (
            self._table, self._query()))
