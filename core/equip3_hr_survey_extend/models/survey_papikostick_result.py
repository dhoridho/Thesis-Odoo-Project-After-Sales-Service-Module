from odoo import models,api,_,fields


class Equip3SurveyPapikostickResult(models.Model):
    _name = 'survey.papikostick_result'
    survey_user_input = fields.Many2one('survey.user_input')
    # line = fields.Integer()
    g_field = fields.Integer()
    l_field = fields.Integer()
    i_field = fields.Integer()
    t_field = fields.Integer()
    v_field = fields.Integer()
    s_field = fields.Integer()
    r_field = fields.Integer()
    d_field = fields.Integer()
    c_field = fields.Integer()
    e_field = fields.Integer()
    n_field = fields.Integer()
    a_field = fields.Integer()
    p_field = fields.Integer()
    x_field = fields.Integer()
    b_field = fields.Integer()
    o_field = fields.Integer()
    z_field = fields.Integer()
    k_field = fields.Integer()
    f_field = fields.Integer()
    w_field = fields.Integer()
    total_field = fields.Integer()


class Equip3SurveyPapikostickParameter(models.Model):
    _name = 'survey.papikostick_parameter_result'
    
    survey_user_input = fields.Many2one('survey.user_input')
    parameter = fields.Char()
    description = fields.Text()
    code_pl = fields.Text()
    description_code = fields.Text()
    score_code = fields.Text()
    analysis = fields.Text()
    score = fields.Float()
