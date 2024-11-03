from odoo import models,api,_,fields


class Equip3SurveyDiscResult(models.Model):
    _name = 'survey.disc_result'
    survey_user_input = fields.Many2one('survey.user_input')
    line = fields.Integer()
    d_field = fields.Integer()
    i_field = fields.Integer()
    s_field = fields.Integer()
    c_field = fields.Integer()
    star_field = fields.Integer()
    total_field = fields.Integer()


class Equip3SurveyDiscResultScore2(models.Model):
    _name = 'survey.disc_result.score2'
    survey_user_input = fields.Many2one('survey.user_input')
    line = fields.Integer()
    d_field = fields.Float()
    i_field = fields.Float()
    s_field = fields.Float()
    c_field = fields.Float()


class Equip3SurveyDiscResultScore3(models.Model):
    _name = 'survey.disc_result.score3'
    survey_user_input = fields.Many2one('survey.user_input')
    line = fields.Integer()
    c_fields = fields.Integer()
    d_fields = fields.Integer()
    c_d_fields = fields.Integer()
    i_d_fields = fields.Integer()
    i_d_c_fields = fields.Integer()
    i_d_s_fields = fields.Integer()
    i_s_d_fields = fields.Integer()
    s_d_c_fields = fields.Integer()
    d_i_fields = fields.Integer()
    d_i_s_fields = fields.Integer()
    d_s_fields = fields.Integer()
    c_i_s_fields = fields.Integer()
    c_s_i_fields = fields.Integer()
    i_s_c_i_c_s_fields = fields.Integer()
    s_fields = fields.Integer()
    c_s_fields = fields.Integer()
    s_c_fieds = fields.Integer()
    d_c_fields = fields.Integer()
    d_i_c_fields = fields.Integer()
    d_s_i_fields = fields.Integer()
    d_s_c_fields = fields.Integer()
    d_c_i_fields = fields.Integer()
    d_c_s_fields = fields.Integer()
    i_fields = fields.Integer()
    i_s_fields = fields.Integer()
    i_c_fields = fields.Integer()
    i_c_d_fields = fields.Integer()
    i_c_s_fields  = fields.Integer()
    s_d_fields = fields.Integer()
    s_i_fields = fields.Integer()
    s_d_i_fields = fields.Integer()
    s_i_d_fields = fields.Integer()
    s_i_c_fields = fields.Integer()
    s_c_d_fields = fields.Integer()
    s_c_i_fields = fields.Integer()
    c_i_fields = fields.Integer()
    c_d_i_fields = fields.Integer()
    c_d_s_fields = fields.Integer()
    c_i_d_fields = fields.Integer()
    c_s_d_fields = fields.Integer()
    match_score = fields.Integer()


