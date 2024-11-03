import werkzeug
from odoo import fields, models, api


class hashMicroInheritSurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'
    survey_start_url = fields.Char('Survey URL', compute='_compute_survey_start_url',readonly=False)
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True)
    


    @api.depends('survey_id.access_token')
    def _compute_survey_start_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for invite in self:
            invite.survey_start_url = werkzeug.urls.url_join(base_url,
                                                             invite.survey_id.get_start_url()) if invite.survey_id else False
