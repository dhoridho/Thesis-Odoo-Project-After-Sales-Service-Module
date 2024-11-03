from logging import PercentStyle
import re
from odoo import models,api,_,fields
import pandas as pd
import plotly
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import requests
import json
import base64
from odoo.tools.mimetypes import guess_mimetype
from odoo.modules import get_module_path
import odoo.tools as tools1
import cv2
import tempfile
import base64

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.client import AccessTokenCredentials
from pytube import YouTube 
import datetime as datetime1
import sys
from odoo.exceptions import ValidationError

sys.setrecursionlimit(5000)

def openerfile(path, flags):
    return os.open(path, flags, 0o777)

class Equip3SurveyInheritSurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    survey_type = fields.Char(compute='_get_survey_type',store=True)
    disc_result_ids = fields.One2many('survey.disc_result','survey_user_input')
    disc_result_score2_ids = fields.One2many('survey.disc_result.score2','survey_user_input')
    disc_result_score3_ids = fields.One2many('survey.disc_result.score3','survey_user_input')
    epps_result_score_ids = fields.One2many('survey.consistency.result','survey_user_input')
    epps_peronality_result_score_ids = fields.One2many('survey.personality.result','survey_user_input')
    papikostick_result_ids = fields.One2many('survey.papikostick_result','survey_user_input')
    papikostick_parameter_result_ids = fields.One2many('survey.papikostick_parameter_result','survey_user_input')
    interview_result_skill_ids = fields.One2many('survey.interview.skill.result','survey_user_input')
    interview_result_personality_ids = fields.One2many('survey.interview.personality.result','survey_user_input')
    ist_scoring_result_nonmatrix_ids = fields.One2many('ist.scoring.result.nonmatrix','survey_user_input')
    ist_scoring_result_matrix_by_age_ids = fields.One2many('ist.scoring.result.matrix.by.age','survey_user_input')
    ist_scoring_iq_ids = fields.One2many('ist.scoring.iq','survey_user_input')
    ist_scoring_result_ids = fields.One2many('ist.scoring.result','survey_user_input')
    ist_scoring_final_result_ids = fields.One2many('ist.scoring.final.result','survey_user_input')
    ist_mindset_profile_final_result_ids = fields.One2many('ist.mindset.profile.result','survey_user_input')
    mask_public_self = fields.Many2one('survey.disc.variables')
    mask_public_self_code = fields.Char(related="mask_public_self.code")
    core_private_self = fields.Many2one('survey.disc.variables')
    core_private_self_code = fields.Char(related="core_private_self.code")
    mirror_perceived_self = fields.Many2one('survey.disc.variables')
    mirror_perceived_self_code = fields.Char(related="mirror_perceived_self.code")
    mask_public_self_ids = fields.One2many('survey.input.personality.line','mask_public_self')
    core_private_self_ids = fields.One2many('survey.input.personality.line','core_private_self')
    mirror_perceived_self_ids = fields.One2many('survey.input.personality.line','mirror_perceived_self')
    personal_description = fields.Text()
    personal_description_en = fields.Text()
    job_match = fields.Text()
    job_suggestion = fields.Many2many('hr.job',string="Job Suggestion")
    is_hide_generate = fields.Boolean(default=False)
    is_hide_generate_score2 = fields.Boolean(default=True)
    is_hide_generate_score3 = fields.Boolean(default=True)
    is_hide_generate_final_score = fields.Boolean(default=True)
    shadow_field_mask_public_self = fields.Char(compute='_get_mask_public_self')
    shadow_field_core_private_self = fields.Char(compute='_get_core_private_self')
    shadow_field_mirror_perceived_self = fields.Char(compute='_get_mirror_perceived_self')
    skill_score = fields.Integer(compute='_compute_skill_score')
    personality_score = fields.Integer(compute='_compute_personality_score')
    disc_match_score_ids = fields.One2many('disc.match.score','user_input_id')
    vak_score_ids = fields.One2many('survey.input.vak.score','survey_user_input_id')
    chart_epps_result_score = fields.Text(
        string='EPPS Result Score Chart',
        compute='_compute_chart_epps_result_score',
    )
    chart_disc_result_score21 = fields.Text(
        string='Disc Result Score 2 Chart 1',
        compute='_compute_chart_disc_result_score2_1',
    )
    chart_disc_result_score22 = fields.Text(
        string='Disc Result Score 2 Chart 2',
        compute='_compute_chart_disc_result_score2_2',
    )
    chart_disc_result_score23 = fields.Text(
        string='Disc Result Score 2 Chart 3',
        compute='_compute_chart_disc_result_score2_3',
    )
    chart_papikostick_result_score = fields.Text(
        string='Papikostick Result Score Chart',
        compute='_compute_chart_papikostick_result_score',
    )
    chart_ist_result_score = fields.Text(
        string='IST Result Score Chart',
        compute='_compute_chart_ist_result_score',
    )
    mbti_final_result_ids = fields.One2many(
        comodel_name='mbti.final.result',
        inverse_name='survey_user_input'
    )
    mbti_personality_result_ids = fields.One2many(
        comodel_name='mbti.personality.result',
        inverse_name='survey_user_input'
    )
    dimensional_score_ids = fields.One2many(
        comodel_name='mbti.dimensional.score',
        inverse_name='survey_user_input',
        string='Dimensional Score'
    )
    mbti_result = fields.Char(string='MBTI Result', compute='_compute_mbti_result', store=True)
    kraepelin_question_array = fields.Char(string='Question Array')
    kraepelin_answer_array = fields.Char(string='Answer Array')
    kraepelin_test_result_ids = fields.One2many(
        comodel_name='kraepelin.test.result',
        inverse_name='survey_user_input',
        string='Kraepelin Test Result'
    )
    chart_kraepelin_result_score = fields.Text(string='Kraepelin Result Score Chart')
    img_chart_kraepelin_result_score = fields.Text(string='Kraepelin Result Score Image Chart')
    vak_parameter_ids = fields.Many2many('vak.parameter')
    

    @api.depends('mbti_final_result_ids')
    def _compute_mbti_result(self):
        for record in self:
            if record.mbti_final_result_ids:
                for result in record.mbti_final_result_ids:
                    record.mbti_result = result.name
    

    
    def _print_report_custom(self):
        report_print_ids = []
        user_input = self.browse(self.ids)
        no = 0
        for data in user_input:
            no+=1
            if data.survey_type == 'IST':
                x_arr = []
                y_arr = []
                parameters = self.env['ist.parameter.root'].search([])
                for parameter in parameters:
                    x_arr.append(parameter.code)
                
                for data in self:
                    if data.ist_scoring_result_matrix_by_age_ids:

                        for line in data.ist_scoring_result_matrix_by_age_ids:
                            y_arr.append(line.score_se)
                            y_arr.append(line.score_wa)
                            y_arr.append(line.score_an)
                            y_arr.append(line.score_ge)
                            y_arr.append(line.score_ra)
                            y_arr.append(line.score_zr)
                            y_arr.append(line.score_fa)
                            y_arr.append(line.score_wu)
                            y_arr.append(line.score_me)
                        
                coor = [{'x': x_arr, 'y': y_arr}]
                fig = go.Figure(data=coor)

                chart_data = base64.b64encode(fig.to_image(format='png')).decode()
                report_print_ids.append({
                    'no':no,
                    'name':data.applicant_id.partner_name,
                    'email':data.applicant_id.email_from,
                    'test_name':data.survey_id.title,
                    'psychological_category': data.survey_id.category_id.name,
                    'taken_on':datetime.strftime(data.create_date,DEFAULT_SERVER_DATETIME_FORMAT).format("%m/%d/%Y, %H:%M"),
                    'score':data.score_by_amount,
                    'applicant_id': data.applicant_id.applicant_id,
                    'job_position': data.job_id.name,
                    'gender': data.applicant_id.gender,
                    'age': data.applicant_id.birth_years,
                    'survey_type': data.survey_type,
                    'gesamt_score': data.ist_scoring_final_result_ids.gesamt_score,
                    'iq_score': data.ist_scoring_final_result_ids.iq_score,
                    'category': data.ist_scoring_final_result_ids.iq_category,
                    # IST Score
                    'ist_score': data.ist_scoring_result_ids,
                    'grafik_ist': chart_data,
                    'mindset_profile': data.ist_mindset_profile_final_result_ids,
                })
            elif data.survey_type == 'DISC':
                disc_chart = data.generate_image_from_disc_score_chart()
                report_print_ids.append({
                    'no':no,
                    'name':data.applicant_id.partner_name,
                    'email':data.applicant_id.email_from,
                    'test_name':data.survey_id.title,
                    'psychological_category': data.survey_id.category_id.name,
                    'taken_on':datetime.strftime(data.create_date,DEFAULT_SERVER_DATETIME_FORMAT).format("%m/%d/%Y, %H:%M"),                
                    'applicant_id': data.applicant_id.applicant_id,
                    'job_position': data.job_id.name,
                    'gender': data.applicant_id.gender,
                    'age': data.applicant_id.birth_years,
                    'disc_score': data.disc_result_ids,
                    'grafik_score_1': disc_chart['chart1'],
                    'grafik_score_2': disc_chart['chart2'],
                    'grafik_score_3': disc_chart['chart3'],
                    'mask_public_self_code': data.mask_public_self_code,
                    'mask_public_self': data.mask_public_self.personality.personality,
                    'mask_public_self_ids': data.mask_public_self_ids, 
                    'core_private_self_code': data.core_private_self_code,
                    'core_private_self': data.core_private_self.personality.personality,
                    'core_private_self_ids': data.core_private_self_ids,
                    'mirror_perceived_code': data.mirror_perceived_self_code,
                    'mirror_perceived_self': data.mirror_perceived_self.personality.personality,
                    'mirror_perceived_self_ids': data.mirror_perceived_self_ids,
                    'disc_match_score_ids': data.disc_match_score_ids,
                    'personality_description_id': data.personal_description,
                    'personality_description_en': data.personal_description_en,
                    'job_match': data.job_match,
                    'job_suggestion': data.job_suggestion.name,
                    'score':data.score_by_amount,
                    'survey_type': data.survey_type,
                })
            
            elif data.survey_type == 'PAPIKOSTICK':
                report_print_ids.append({
                    'no':no,
                    'name':data.applicant_id.partner_name,
                    'email':data.applicant_id.email_from,
                    'test_name':data.survey_id.title,
                    'psychological_category': data.survey_id.category_id.name,
                    'taken_on':datetime.strftime(data.create_date,DEFAULT_SERVER_DATETIME_FORMAT).format("%m/%d/%Y, %H:%M"),                
                    'applicant_id': data.applicant_id.applicant_id,
                    'job_position': data.job_id.name,
                    'gender': data.applicant_id.gender,
                    'age': data.applicant_id.birth_years,
                    'papikostick_score': data.papikostick_parameter_result_ids,
                    'grafik_papikostick': data.generate_image_from_papikostick_chart()
                })
            
            elif data.survey_type == 'EPPS':
                report_print_ids.append({
                    'no':no,
                    'name':data.applicant_id.partner_name,
                    'email':data.applicant_id.email_from,
                    'test_name':data.survey_id.title,
                    'psychological_category': data.survey_id.category_id.name,
                    'taken_on':datetime.strftime(data.create_date,DEFAULT_SERVER_DATETIME_FORMAT).format("%m/%d/%Y, %H:%M"),                
                    'applicant_id': data.applicant_id.applicant_id,
                    'job_position': data.job_id.name,
                    'gender': data.applicant_id.gender,
                    'age': data.applicant_id.birth_years,
                    'consistency_score':data.epps_result_score_ids,
                    'grafik_epps': data.generate_image_from_epps_chart(),
                    'personality_score':data.epps_peronality_result_score_ids,
                })
            
            elif data.survey_type == 'MBTI':
                personality_dicts = {}
                job_lists = []
                for personality in data.mbti_final_result_ids:
                    for job in personality.job_position:
                        job_lists.append(job.name)
                    for var in data.mbti_personality_result_ids:
                        description_list = var.description.split("-")
                        description_list = [item.strip() for item in description_list if item.strip()]
                        personality_dicts[var.name] =description_list
                    report_print_ids.append({
                        'no':no,
                        'name':data.applicant_id.partner_name,
                        'email':data.applicant_id.email_from,
                        'test_name':data.survey_id.title,
                        'psychological_category': data.survey_id.category_id.name,
                        'taken_on':datetime.strftime(data.create_date,DEFAULT_SERVER_DATETIME_FORMAT).format("%m/%d/%Y, %H:%M"),                
                        'applicant_id': data.applicant_id.applicant_id,
                        'job_position': data.job_id.name,
                        'job_suggestion': ', '.join(job_lists),
                        'gender': data.applicant_id.gender,
                        'age': data.applicant_id.birth_years,
                        'personality_ids': data.mbti_final_result_ids,
                        'dimensional_score_ids': data.dimensional_score_ids,
                        'variable_ids': data.mbti_personality_result_ids,
                        'personality_representation': personality.representation.decode(),
                        'personality_each_dimensions': personality_dicts
                    })

            elif data.survey_type == 'KRAEPELIN':
                report_print_ids.append({
                    'no': no,
                    'name': data.applicant_id.partner_name,
                    'email': data.applicant_id.email_from,
                    'test_name': data.survey_id.title,
                    'psychological_category': data.survey_id.category_id.name,
                    'taken_on': datetime.strftime(data.create_date, DEFAULT_SERVER_DATETIME_FORMAT).format(
                        "%m/%d/%Y, %H:%M"),
                    'applicant_id': data.applicant_id.applicant_id,
                    'job_position': data.job_id.name,
                    'gender': data.applicant_id.gender,
                    'age': data.applicant_id.birth_years,
                    'kraepelin_score': data.kraepelin_test_result_ids,
                    'grafik_kraepelin': data.img_chart_kraepelin_result_score,
                    # 'personality_score': data.epps_peronality_result_score_ids,
                })

            else:
                report_print_ids.append({
                    'no':no,
                    'name':data.applicant_id.partner_name,
                    'email':data.applicant_id.email_from,
                    'test_name':data.survey_id.title,
                    'taken_on':datetime.strftime(data.create_date,DEFAULT_SERVER_DATETIME_FORMAT).format("%m/%d/%Y, %H:%M"),
                    'score':data.score_by_amount,
                    'survey_type': data.survey_type,
                })
        print("user_input")
        print(report_print_ids)
        return report_print_ids
        
        # for record in self:
        #     report_list.append(record.id)

    def action_print_test_result(self): 
        if self.survey_type == 'DISC':
            if self.is_hide_generate:
                return self.env.ref('equip3_hr_survey_extend.report_test_pdf').report_action(self)
            else:
                raise ValidationError("Please Generate before Printing the result")
        else:
            return self.env.ref('equip3_hr_survey_extend.report_test_pdf').report_action(self)   

    def action_print_certificates(self):
        return self.env.ref('survey.certification_report').report_action(self)

    def generate_image_from_epps_chart(self):
        for data in self:
            if data.epps_peronality_result_score_ids:
                x_arr = []
                y_arr = []
                for l in data.epps_peronality_result_score_ids:
                    if l.percentile and l.factor:
                        x_arr.append(l.factor)
                        y_arr.append(l.percentile)
                if x_arr and y_arr:
                    coor = [{'x': x_arr, 'y': y_arr}]
                    fig = go.Figure(data=coor)
                    chart = base64.b64encode(fig.to_image(format='png')).decode()

                    return chart

    def generate_image_from_papikostick_chart(self):
        for data in self:
            if data.papikostick_result_ids:
                x_arr = ['G/Role of Hard Intense Worker', 'L/Leadership Role', 'I/Ease in Decision Making', 'T/"On The Go" Type', 'V/Vigorous Type', 'S/Social Extension', 'R/Theoretical Type', 'D/Interest in Working with Details', 'C/Organized type', 'E/Emotional Restraint', 'N/Need to Personality Finish a Task', 'A/Need to Achieve', 'P/Need to Control Others', 'X/Need to be Noticed', 'B/Need to Belong to Group', 'O/Need for Closeness and Affection', 'Z/Need for Change', 'K/Need for Defensive Aggressiveness', 'F/Need to Support Authority', 'W/Need for Rule and Supervision']
                y_arr = []

                for line in data.papikostick_result_ids:
                    y_arr.append(line.n_field)
                    y_arr.append(line.g_field)
                    y_arr.append(line.a_field)
                    y_arr.append(line.l_field)
                    y_arr.append(line.p_field)
                    y_arr.append(line.i_field)
                    y_arr.append(line.t_field)
                    y_arr.append(line.v_field)
                    y_arr.append(line.x_field)
                    y_arr.append(line.s_field)
                    y_arr.append(line.b_field)
                    y_arr.append(line.o_field)
                    y_arr.append(line.r_field)
                    y_arr.append(line.d_field)
                    y_arr.append(line.c_field)
                    y_arr.append(line.z_field)
                    y_arr.append(line.e_field)
                    y_arr.append(line.k_field)
                    y_arr.append(line.f_field)
                    y_arr.append(line.w_field)
                
                if x_arr and y_arr:
                    df = pd.DataFrame(dict(r=y_arr, theta=x_arr))
                    fig = px.line_polar(df, r='r', theta='theta', line_close=True)
                    chart = base64.b64encode(fig.to_image(format='png')).decode()

                return chart


    def generate_image_from_disc_score_chart(self):
        for data in self:
            if data.disc_result_score2_ids:
                x_arr1 = []
                y_arr1 = []
                x_arr2 = []
                y_arr2 = []
                x_arr3 = []
                y_arr3 = []
                for l in data.disc_result_score2_ids:
                    if l.line == 1:
                        x_arr1.append('D')
                        y_arr1.append(l.d_field)
                    if l.line == 1:
                        x_arr1.append('I')
                        y_arr1.append(l.i_field)
                    if l.line == 1:
                        x_arr1.append('S')
                        y_arr1.append(l.s_field)
                    if l.line == 1:
                        x_arr1.append('C')
                        y_arr1.append(l.c_field)

                    if l.line == 2:
                        x_arr2.append('D')
                        y_arr2.append(l.d_field)
                    if l.line == 2:
                        x_arr2.append('I')
                        y_arr2.append(l.i_field)
                    if l.line == 2:
                        x_arr2.append('S')
                        y_arr2.append(l.s_field)
                    if l.line == 2:
                        x_arr2.append('C')
                        y_arr2.append(l.c_field)

                    if l.line == 3:
                        x_arr3.append('D')
                        y_arr3.append(l.d_field)
                    if l.line == 3:
                        x_arr3.append('I')
                        y_arr3.append(l.i_field)
                    if l.line == 3:
                        x_arr3.append('S')
                        y_arr3.append(l.s_field)
                    if l.line == 3:
                        x_arr3.append('C')
                        y_arr3.append(l.c_field)
                        
                coor1 = [{'x': x_arr1, 'y': y_arr1}]
                coor2 = [{'x': x_arr2, 'y': y_arr2}]
                coor3 = [{'x': x_arr3, 'y': y_arr3}]

                figure1 = go.Figure(data=coor1)
                figure2 = go.Figure(data=coor2)
                figure3 = go.Figure(data=coor3)

                chart1 = base64.b64encode(figure1.to_image(format='png')).decode()
                chart2 = base64.b64encode(figure2.to_image(format='png')).decode()
                chart3 = base64.b64encode(figure3.to_image(format='png')).decode()

                chart_data = {
                    'chart1': chart1,
                    'chart2': chart2,
                    'chart3': chart3
                }

                return chart_data

    def _compute_chart_disc_result_score2_1(self):
        for data in self:
            chart_disc_result_score2_1 = False
            if data.disc_result_score2_ids:
                x_arr = []
                y_arr = []
                for l in data.disc_result_score2_ids:
                    if l.line == 1:
                        x_arr.append('D')
                        y_arr.append(l.d_field)
                    if l.line == 1:
                        x_arr.append('I')
                        y_arr.append(l.i_field)
                    if l.line == 1:
                        x_arr.append('S')
                        y_arr.append(l.s_field)
                    if l.line == 1:
                        x_arr.append('C')
                        y_arr.append(l.c_field)
                    if l.line == 1 and x_arr and y_arr:
                        break
                if x_arr and y_arr:
                    coor = [{'x': x_arr, 'y': y_arr}]
                    chart_disc_result_score2_1 = plotly.offline.plot(coor,
                                             include_plotlyjs=False,
                                             output_type='div')
            data.chart_disc_result_score21 = chart_disc_result_score2_1


    def _compute_chart_disc_result_score2_2(self):
        for data in self:
            chart_disc_result_score2_2 = False
            if data.disc_result_score2_ids:
                x_arr = []
                y_arr = []
                for l in data.disc_result_score2_ids:
                    if l.line == 2 :
                        x_arr.append('D')
                        y_arr.append(l.d_field)
                    if l.line == 2 :
                        x_arr.append('I')
                        y_arr.append(l.i_field)
                    if l.line == 2 :
                        x_arr.append('S')
                        y_arr.append(l.s_field)
                    if l.line == 2 :
                        x_arr.append('C')
                        y_arr.append(l.c_field)
                    if l.line == 2 and x_arr and y_arr:
                        break
                if x_arr and y_arr:
                    coor = [{'x': x_arr, 'y': y_arr}]
                    chart_disc_result_score2_2 = plotly.offline.plot(coor,
                                             include_plotlyjs=False,
                                             output_type='div')
            data.chart_disc_result_score22 = chart_disc_result_score2_2

    def _compute_chart_disc_result_score2_3(self):
        for data in self:
            chart_disc_result_score2_3 = False
            if data.disc_result_score2_ids:
                x_arr = []
                y_arr = []
                for l in data.disc_result_score2_ids:
                    if l.line == 3 :
                        x_arr.append('D')
                        y_arr.append(l.d_field)
                    if l.line == 3 :
                        x_arr.append('I')
                        y_arr.append(l.i_field)
                    if l.line == 3 :
                        x_arr.append('S')
                        y_arr.append(l.s_field)
                    if l.line == 3 :
                        x_arr.append('C')
                        y_arr.append(l.c_field)
                    if l.line == 3 and x_arr and y_arr:
                        break
                if x_arr and y_arr:
                    coor = [{'x': x_arr, 'y': y_arr}]
                    chart_disc_result_score2_3 = plotly.offline.plot(coor,
                                             include_plotlyjs=False,
                                             output_type='div')
            data.chart_disc_result_score23 = chart_disc_result_score2_3
    
    def _compute_chart_ist_result_score(self):
        x_arr = []
        parameters = self.env['ist.parameter.root'].search([])
        for parameter in parameters:
            x_arr.append(parameter.code)
        
        for data in self:
            chart_ist_result_score = False
            if data.ist_scoring_result_matrix_by_age_ids:
                y_arr = []

                for line in data.ist_scoring_result_matrix_by_age_ids:
                    y_arr.append(line.score_se)
                    y_arr.append(line.score_wa)
                    y_arr.append(line.score_an)
                    y_arr.append(line.score_ge)
                    y_arr.append(line.score_ra)
                    y_arr.append(line.score_zr)
                    y_arr.append(line.score_fa)
                    y_arr.append(line.score_wu)
                    y_arr.append(line.score_me)
                
                if x_arr and y_arr:
                    coor = [{'x': x_arr, 'y': y_arr}]
                    chart_ist_result_score = plotly.offline.plot(coor,
                                             include_plotlyjs=False,
                                             output_type='div')
            data.chart_ist_result_score = chart_ist_result_score

    def _compute_chart_epps_result_score(self):
        for data in self:
            chart_epps_result_score = False
            if data.epps_peronality_result_score_ids:
                x_arr = []
                y_arr = []
                for l in data.epps_peronality_result_score_ids:
                    if l.percentile and l.factor:
                        x_arr.append(l.factor)
                        y_arr.append(l.percentile)
                if x_arr and y_arr:
                    coor = [{'x': x_arr, 'y': y_arr}]
                    chart_epps_result_score = plotly.offline.plot(coor,
                                             include_plotlyjs=False,
                                             output_type='div')
            data.chart_epps_result_score = chart_epps_result_score
    
    def _compute_chart_papikostick_result_score(self):
        for data in self:
            chart_papikostick_result_score = False
            if data.papikostick_result_ids:
                x_arr = ['G/Role of Hard Intense Worker', 'L/Leadership Role', 'I/Ease in Decision Making', 'T/"On The Go" Type', 'V/Vigorous Type', 'S/Social Extension', 'R/Theoretical Type', 'D/Interest in Working with Details', 'C/Organized type', 'E/Emotional Restraint', 'N/Need to Personality Finish a Task', 'A/Need to Achieve', 'P/Need to Control Others', 'X/Need to be Noticed', 'B/Need to Belong to Group', 'O/Need for Closeness and Affection', 'Z/Need for Change', 'K/Need for Defensive Aggressiveness', 'F/Need to Support Authority', 'W/Need for Rule and Supervision']
                y_arr = []

                for line in data.papikostick_result_ids:
                    y_arr.append(line.n_field)
                    y_arr.append(line.g_field)
                    y_arr.append(line.a_field)
                    y_arr.append(line.l_field)
                    y_arr.append(line.p_field)
                    y_arr.append(line.i_field)
                    y_arr.append(line.t_field)
                    y_arr.append(line.v_field)
                    y_arr.append(line.x_field)
                    y_arr.append(line.s_field)
                    y_arr.append(line.b_field)
                    y_arr.append(line.o_field)
                    y_arr.append(line.r_field)
                    y_arr.append(line.d_field)
                    y_arr.append(line.c_field)
                    y_arr.append(line.z_field)
                    y_arr.append(line.e_field)
                    y_arr.append(line.k_field)
                    y_arr.append(line.f_field)
                    y_arr.append(line.w_field)
                
                if x_arr and y_arr:
                    df = pd.DataFrame(dict(r=y_arr, theta=x_arr))
                    fig = px.line_polar(df, r='r', theta='theta', line_close=True)
                    chart_papikostick_result_score = plotly.offline.plot(fig,
                                             include_plotlyjs=False,
                                             output_type='div')
                                             
            data.chart_papikostick_result_score = chart_papikostick_result_score
                    
    
    @api.depends('interview_result_skill_ids')
    def _compute_skill_score(self):
        for record in self:
            if record.interview_result_skill_ids:
                score = 0
                for data_score in record.interview_result_skill_ids:
                    if data_score.score == '1':
                        score += 2
                    if data_score.score == '2':
                        score += 4
                    if data_score.score == '3':
                        score += 6
                    if data_score.score == '4':
                        score += 8
                    if data_score.score == '5':
                        score += 10
                jml_data = len(record.interview_result_skill_ids)
                avg_score = score/jml_data
                record.skill_score = avg_score * 10
            else:
                record.skill_score = 0
                
    @api.depends('interview_result_personality_ids')
    def _compute_personality_score(self):
        for record in self:
            if record.interview_result_personality_ids:
                score = 0
                for data_score in record.interview_result_personality_ids:
                    if data_score.score == '1':
                        score += 2
                    if data_score.score == '2':
                        score += 4
                    if data_score.score == '3':
                        score += 6
                    if data_score.score == '4':
                        score += 8
                    if data_score.score == '5':
                        score += 10
                jml_data = len(record.interview_result_skill_ids)
                avg_score = score/jml_data
                record.personality_score = avg_score * 10
            else:
                record.personality_score = 0  
                
                            
                        
    
    
    
    
    
    def generate_interview_score(self):
         for record in self:
             skill_ids = []
             personality_ids = []
             for question_skills in record.user_input_line_ids.filtered(lambda line:line.question_id.interview_category == 'skills' and not line.question_id.comment_parent_id):
                 score_str = str(int(question_skills.answer_score))
                 comment = record.user_input_line_ids.filtered(lambda line:line.question_id.comment_parent_id.id == question_skills.question_id.id)
                 skill_ids.append((0,0,{'question':question_skills.question_id.title,'score':score_str,'comment':comment.value_char_box if comment else False}))
             record.interview_result_skill_ids = skill_ids
             for question in record.user_input_line_ids.filtered(lambda line:line.question_id.interview_category == 'personality' and not line.question_id.comment_parent_id):
                score_str = str(int(question.answer_score)) if question.answer_score else '0'
                comment = record.user_input_line_ids.filtered(lambda line:line.question_id.comment_parent_id.id == question.question_id.id)
                personality_ids.append((0,0,{'question':question.question_id.title,'score':score_str,'comment':comment.value_char_box if comment else False}))
             record.interview_result_personality_ids = personality_ids
             record.applicant_id.interview_id = record.id
             
    
    def epps_category(self,percentile):
        category = ""
        if percentile <= 3:
            category = "Sangat Pembohong"
        elif percentile <= 16:
            category = "Pembohong"
        elif percentile <= 84:
            category = "Cukup Jujur"
        elif percentile <= 96:
            category = "Jujur"
        elif percentile > 96:
            category = "Sangat Jujur"
        return category
    
    def epps_personality_category(self,percentile):
        category = ""
        if percentile <= 3:
            category = "Sangat Rendah"
        elif percentile <= 16:
            category = "Rendah"
        elif percentile <= 84:
            category = "Sedang"
        elif percentile <= 96:
            category = "Tinggi"
        elif percentile > 96:
            category = "Sangat Tinggi"
        return category
            
    def has_numbers(self,inputString):
        return any(char.isdigit() for char in inputString)
    
    
    def generate_vak(self):
        for record in self:
            vak_score = []
            result = ''
            if record.user_input_line_ids:
                v_score = len(record.user_input_line_ids.filtered(lambda line:line.vak_selection == 'v'))
                v_percentage = (v_score/30)*100
                interpretation_v = ''
                if v_percentage >= 40:
                    interpretation_v = 'dominan'
                elif v_percentage >= 21 and v_percentage <= 39:
                    interpretation_v = 'sekunder'
                else:
                    interpretation_v = 'non_dominan'
                if interpretation_v in ('dominan','sekunder'):
                    result += 'V'
                vak_score.append((0,0,{'vak_code':'V','total':v_score,'percentage':v_percentage,'interpretation':interpretation_v}))
                
                a_score = len(record.user_input_line_ids.filtered(lambda line:line.vak_selection == 'a'))
                a_percentage = (a_score/30)*100  
                interpretation_a = ''
                if a_percentage >= 40:
                    interpretation_a = 'dominan'
                elif a_percentage >= 21 and a_percentage <= 39:
                    interpretation_a = 'sekunder'
                else:
                    interpretation_a = 'non_dominan'
                    
                if interpretation_a in ('dominan','sekunder'):
                    result += 'A'
                vak_score.append((0,0,{'vak_code':'A','total':a_score,'percentage':a_percentage,'interpretation':interpretation_a}))
                
                k_score = len(record.user_input_line_ids.filtered(lambda line:line.vak_selection == 'k'))
                k_percentage = (k_score/30)*100  
                interpretation_k = ''
                if k_percentage >= 40:
                    interpretation_k = 'dominan'
                elif k_percentage >= 21 and k_percentage <= 39:
                    interpretation_k = 'sekunder'
                else:
                    interpretation_k = 'non_dominan'
                if interpretation_k in ('dominan','sekunder'):
                    result += 'K'
                vak_score.append((0,0,{'vak_code':'K','total':k_score,'percentage':k_percentage,'interpretation':interpretation_k}))
                
            record.vak_score_ids = vak_score
            vak_parameter = self.env['vak.parameter'].sudo().search([('vak_code','=',result)])
            if vak_parameter:
                record.vak_parameter_ids = vak_parameter.ids
            
            
        
    
    def generate_epps(self):
        for record in self:
            if record.user_input_line_ids:
                code = 1
                for data_epps_code in record.user_input_line_ids:
                    if data_epps_code.suggested_answer_id:
                        if data_epps_code.suggested_answer_id.epps_code == 1:
                            code = 1
                        elif data_epps_code.suggested_answer_id.epps_code == 2:
                            code = 2
                        elif data_epps_code.suggested_answer_id.epps_code == 3:
                            code = 3
                        elif data_epps_code.suggested_answer_id.epps_code == 4:
                            code = 4
                        
                                    
                C1 = 0
                C2 = 0
                C3 = 0
                C4 = 0
                C5 = 0
                C6 = 0
                C7 = 0
                C8 = 0
                C9 = 0
                C10 = 0
                C11 = 0
                C12 = 0
                C13 = 0
                C14 = 0
                C15 = 0
                score_len = []
                
                no_1 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "1" )
                no_2 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "2"  )
                no_3 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "3" )
                no_4 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "4" )
                no_5 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "5" )
                no_6 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "6")
                no_7 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "7")
                no_8 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "8")
                no_9 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "9")
                no_10 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "10")
                no_11 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "11")
                no_12 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "12")
                no_13 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "13")
                no_14 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "14")
                no_15 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "15")
                no_16 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "16")
                no_17 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "17")
                no_18 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "18")
                no_19 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "19")
                no_20 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "20")
                no_21 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "21")
                no_22 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "22")
                no_23 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "23")
                no_24 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "24")
                no_25 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "25")
                no_26 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "26")
                no_27 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "27")
                no_28 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "28")
                no_29 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "29")
                no_30 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "30")
                no_31 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "31")
                no_32 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "32")
                no_33 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "33")
                no_34 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "34")
                no_35 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "35")
                no_36 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "36")
                no_37 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "37")
                no_38 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "38")
                no_39 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "39")
                no_40 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "40")
                no_41 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "41")
                no_42 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "42")
                no_43 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "43")
                no_44 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "44")
                no_45 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "45")
                no_46 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "46")
                no_47 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "47")
                no_48 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "48")
                no_49 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "49")
                no_50 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "50")
                no_51 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "51" )
                no_52 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "52" )
                no_53 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "53" )
                no_54 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "54" )
                no_55 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "55" )
                no_56 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "56" )
                no_57 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "57" )
                no_58 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "58" )
                no_59 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "59" )
                no_60 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "60" )
                no_61 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "61" )
                no_62 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "62" )
                no_63 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "63" )
                no_64 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "64" )
                no_65 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "65" )
                no_66 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "66" )
                no_67 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "67" )
                no_68 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "68" )
                no_69 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "69" )
                no_70 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "70" )
                no_71 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "71" )
                no_72 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "72" )
                no_73 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "73" )
                no_74 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "74" )
                no_75 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "75" )
                no_76 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "76" )
                no_77 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "77" )
                no_78 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "78")
                no_79 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "79" )
                no_80 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "80")
                no_81 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "81")
                no_82 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "82")
                no_83 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "83")
                no_84 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "84")
                no_85 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "85")
                no_86 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "86")
                no_87 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "87")
                no_88 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "88")
                no_89 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "89")
                no_90 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "90")
                no_91 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "91")
                no_92 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "92")
                no_93 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "93")
                no_94 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "94")
                no_95 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "95")
                no_96 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "96")
                no_97 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "97")
                no_98 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "98")
                no_99 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "99")
                no_100 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "100")
                no_101 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "101")
                no_102 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "102")
                no_103 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "103")
                no_104 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "104")
                no_105 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "105")
                no_106 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "106")
                no_107 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "107")
                no_108 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "108")
                no_109 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "109")
                no_110 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "110")
                no_111 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "111")
                no_112 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "112")
                no_113 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "113")
                no_114 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "114")
                no_115 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "115")
                no_116 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "116")
                no_117 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "117")
                no_118 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "118")
                no_119 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "119")
                no_120 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "120")
                no_121 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "121")
                no_122 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "122")
                no_123 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "123")
                no_124 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "124")
                no_125 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "125")
                no_126 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "126")
                no_127 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "127")
                no_128 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "128")
                no_129 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "129")
                no_130 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "130")
                no_131 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "131")
                no_132 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "132")
                no_133 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "133")
                no_134 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "134")
                no_135 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "135")
                no_136 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "136")
                no_137 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "137")
                no_138 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "138")
                no_139 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "139")
                no_140 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "140")
                no_141 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "141")
                no_142 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "142")
                no_143 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "143")
                no_144 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "144")
                no_145 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "145")
                no_146 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "146")
                no_147 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "147")
                no_148 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "148")
                no_149 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "149")
                no_150 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "150")
                no_151 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "151")
                no_152 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "152")
                no_153 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "153")
                no_154 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "154")
                no_155 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "155")
                no_156 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "156")
                no_157 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "157")
                no_158 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "158")
                no_159 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "159")
                no_160 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "160")
                no_161 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "161")
                no_162 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "162")
                no_163 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "163")
                no_164 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "164")
                no_165 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "165")
                no_166 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "166")
                no_167 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "167")
                no_168 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "168")
                no_169 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "169")
                no_170 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "170")
                no_171 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "171")
                no_172 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "172")
                no_173 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "173")
                no_174 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "174")
                no_175 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "175")
                no_176 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "176")
                no_177 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "177")
                no_178 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "178")
                no_179 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "179")
                no_180 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "180")
                no_181 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "181")
                no_182 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "182")
                no_183 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "183")
                no_184 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "184")
                no_185 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "185")
                no_186 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "186")
                no_187 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "187")
                no_188 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "188")
                no_189 = record.user_input_line_ids.filtered(lambda line: line.question_id.title  == "189")
                no_190 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "190")
                no_191 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "191")
                no_192 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "192")
                no_193 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "193")
                no_194 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "194")
                no_195 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "195")
                no_196 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "196")
                no_197 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "197")
                no_198 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "198")
                no_199 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "199")
                no_200 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "200")
                no_201 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "201")
                no_202 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "202")
                no_203 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "203")
                no_204 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "204")
                no_205 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "205")
                no_206 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "206")
                no_207 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "207")
                no_208 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "208")
                no_209 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "209")
                no_210 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "210")
                no_211 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "211")
                no_212 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "212")
                no_213 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "213")
                no_214 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "214")
                no_215 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "215")
                no_216 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "216")
                no_217 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "217")
                no_218 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "218")
                no_219 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "219")
                no_220 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "220")
                no_221 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "221")
                no_222 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "222")
                no_223 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "223")
                no_224 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "224")
                no_225 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "225")
                
                    
                
                
                if no_1 and no_151:
                    if no_1.suggested_answer_id.code == no_151.suggested_answer_id.code:
                        C1 = 1
                        score_len.append(C1)
                if no_7 and no_157:
                    if no_7.suggested_answer_id.code == no_157.suggested_answer_id.code:
                        C2 = 1
                        score_len.append(C2)
                if no_13 and no_163:
                    if no_13.suggested_answer_id.code == no_163.suggested_answer_id.code:
                        C3 = 1
                        score_len.append(C3)
                if no_19 and no_169:
                    if no_19.suggested_answer_id.code == no_169.suggested_answer_id.code:
                        C4 = 1
                        score_len.append(C4)
                if no_25 and no_175:
                    if no_25.suggested_answer_id.code == no_175.suggested_answer_id.code:
                        C5 = 1
                        score_len.append(C5)
                if no_26 and no_101:
                    if no_26.suggested_answer_id.code == no_101.suggested_answer_id.code:
                        C6 = 1
                        score_len.append(C6)
                if no_32 and no_107:
                    if no_32.suggested_answer_id.code == no_107.suggested_answer_id.code:
                        C7 = 1
                        score_len.append(C7)
                if no_38 and no_113:
                    if no_38.suggested_answer_id.code == no_113.suggested_answer_id.code:
                        C8 = 1
                        score_len.append(C8)
                if no_44 and no_119:
                    if no_44.suggested_answer_id.code == no_119.suggested_answer_id.code:
                        C9 = 1
                        score_len.append(C9)
                if no_50 and no_125:
                    if no_50.suggested_answer_id.code == no_125.suggested_answer_id.code:
                        C10 = 1
                        score_len.append(C10)
                if no_51 and no_201:
                    if no_51.suggested_answer_id.code == no_201.suggested_answer_id.code:
                        C11 = 1
                        score_len.append(C11)
                if no_57 and no_207:
                    if no_57.suggested_answer_id.code == no_207.suggested_answer_id.code:
                        C12 = 1
                        score_len.append(C12)
                if no_63 and no_213:
                    if no_63.suggested_answer_id.code == no_213.suggested_answer_id.code:
                        C13 = 1
                        score_len.append(C13)
                if no_69 and no_219:
                    if no_69.suggested_answer_id.code == no_219.suggested_answer_id.code:
                        C14 = 1
                        score_len.append(C14)
                if no_75 and no_225:
                    if no_75.suggested_answer_id.code == no_225.suggested_answer_id.code:
                        C15 = 1
                        score_len.append(C15)
                percentile = 0
                category = ""
                scoring_matrix = self.env['survey.epps.scoring.matrix'].search([('code','=',code)],limit=1)
                if scoring_matrix:
                    line_data = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == len(score_len))
                    percentile = line_data.consistency
                    category = self.epps_category(percentile)
                    
                record.epps_result_score_ids = [(0,0,{
                                                    'factor':"Con",
                                                    'c1':C1,
                                                    'c2':C2,
                                                    'c3':C3,
                                                    'c4':C4,
                                                    'c5':C5,
                                                    'c6':C6,
                                                    'c7':C7,
                                                    'c8':C8,
                                                    'c9':C9,
                                                    'c10':C10,
                                                    'c11':C11,
                                                    'c12':C12,
                                                    'c13':C13,
                                                    'c14':C14,
                                                    'c15':C15,
                                                    'score':len(score_len),
                                                    'percentile':percentile,
                                                    'category':category
                                                    
                                                    })]
                ach_r1 = 0                 
                ach_r2 = 0                 
                ach_r3 = 0                 
                ach_r4 = 0                 
                ach_r5 = 0                 
                ach_r6 = 0                 
                ach_r7 = 0                 
                ach_r8 = 0                 
                ach_r9 = 0                 
                ach_r10 = 0                 
                ach_r11 = 0                 
                ach_r12 = 0                 
                ach_r13 = 0                 
                ach_r14 = 0                 
                ach_r = 0
                ach_c = 0
                ach_r_score_len = []
                ach_c_score_len = []
                personality_ids = []
                ach_c1 = 0                                  
                ach_c2 = 0                                  
                ach_c3 = 0                                  
                ach_c4 = 0                                  
                ach_c5 = 0                                  
                ach_c6 = 0                                  
                ach_c7 = 0                                  
                ach_c8 = 0                                  
                ach_c9 = 0                                  
                ach_c10 = 0                                  
                ach_c11 = 0                                  
                ach_c12 = 0                                  
                ach_c13 = 0                                  
                ach_c14 = 0                                  
                ach_c = 0
                if no_6:
                    if no_6.suggested_answer_id.code == "a":
                        ach_r1 = 1
                        ach_r_score_len.append(ach_r1)
                if no_11:
                    if no_11.suggested_answer_id.code == "a":
                        ach_r2 = 1
                        ach_r_score_len.append(ach_r2)
                if no_16:
                    if no_16.suggested_answer_id.code == "a":
                        ach_r3 = 1
                        ach_r_score_len.append(ach_r3)
                if no_21:
                    if no_21.suggested_answer_id.code == "a":
                        ach_r4 = 1
                        ach_r_score_len.append(ach_r4)
                if no_26:
                    if no_26.suggested_answer_id.code == "a":
                        ach_r5 = 1
                        ach_r_score_len.append(ach_r5)
                if no_31:
                        if no_31.suggested_answer_id.code == "a":
                            ach_r6 = 1
                            ach_r_score_len.append(ach_r6) 
                if no_36:
                        if no_36.suggested_answer_id.code == "a":
                            ach_r7 = 1
                            ach_r_score_len.append(ach_r7) 
                if no_41:
                        if no_41.suggested_answer_id.code == "a":
                            ach_r8 = 1
                            ach_r_score_len.append(ach_r8) 
                if no_46:
                        if no_46.suggested_answer_id.code == "a":
                            ach_r9 = 1
                            ach_r_score_len.append(ach_r9) 
                if no_51:
                        if no_51.suggested_answer_id.code == "a":
                            ach_r10 = 1
                            ach_r_score_len.append(ach_r10) 
                if no_56:
                        if no_56.suggested_answer_id.code == "a":
                            ach_r11 = 1
                            ach_r_score_len.append(ach_r11) 
                if no_61:
                    if no_61.suggested_answer_id.code == "a":
                        ach_r12 = 1
                        ach_r_score_len.append(ach_r12)
                if no_66:
                        if no_66.suggested_answer_id.code == "a":
                            ach_r13 = 1
                            ach_r_score_len.append(ach_r13)
                if no_71:
                        if no_71.suggested_answer_id.code == "a":
                            ach_r14 = 1
                            ach_r_score_len.append(ach_r14)
                ach_r = len(ach_r_score_len)
                
                if no_2:
                        if no_2.suggested_answer_id.code == "b":
                            ach_c1 = 1
                            ach_c_score_len.append(ach_c1)
                if no_3:
                        if no_3.suggested_answer_id.code == "b":
                            ach_c2 = 1
                            ach_c_score_len.append(ach_c2)
                if no_4:
                        if no_4.suggested_answer_id.code == "b":
                            ach_c3 = 1
                            ach_c_score_len.append(ach_c3)
                if no_5:
                        if no_5.suggested_answer_id.code == "b":
                            ach_c4 = 1
                            ach_c_score_len.append(ach_c4)
                if no_76:
                        if no_76.suggested_answer_id.code == "b":
                            ach_c5 = 1
                            ach_c_score_len.append(ach_c5)
                if no_77:
                        if no_77.suggested_answer_id.code == "b":
                            ach_c6 = 1
                            ach_c_score_len.append(ach_c6)
                if no_78:
                        if no_78.suggested_answer_id.code == "b":
                            ach_c7 = 1
                            ach_c_score_len.append(ach_c7)
                if no_79:
                        if no_79.suggested_answer_id.code == "b":
                            ach_c8 = 1
                            ach_c_score_len.append(ach_c8)
                if no_80:
                        if no_80.suggested_answer_id.code == "b":
                            ach_c9 = 1
                            ach_c_score_len.append(ach_c9)
                if no_151:
                        if no_151.suggested_answer_id.code == "b":
                            ach_c10 = 1
                            ach_c_score_len.append(ach_c10)
                if no_152:
                        if no_152.suggested_answer_id.code == "b":
                            ach_c11 = 1
                            ach_c_score_len.append(ach_c11)
                if no_153:
                        if no_153.suggested_answer_id.code == "b":
                            ach_c12 = 1
                            ach_c_score_len.append(ach_c12)
                if no_154:
                        if no_154.suggested_answer_id.code == "b":
                            ach_c13 = 1
                            ach_c_score_len.append(ach_c13)
                if no_155:
                        if no_155.suggested_answer_id.code == "b":
                            ach_c14 = 1
                            ach_c_score_len.append(ach_c14)
                ach_c =  len(ach_c_score_len)
                            
                ach_rs = ach_r + ach_c
                ach_category = ""
                if scoring_matrix:
                        line_data_ach = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == ach_rs)
                        epps_personality =  self.env['survey.epps_personality'].search([('sequence','=',1)])
                        percentile_ach = line_data_ach.achievement
                        ach_category = self.epps_personality_category(percentile_ach)
                        personality_ids.append((0,0,{
                                                    'factor':"ach",
                                                    'r1':ach_r1,
                                                        'r2':ach_r2,
                                                        'r3':ach_r3,
                                                        'r4':ach_r4,
                                                        'r5':ach_r5,
                                                        'r6':ach_r6,
                                                        'r7':ach_r7,
                                                        'r8':ach_r8,
                                                        'r9':ach_r9,
                                                        'r10':ach_r10,
                                                        'r11':ach_r11,
                                                        'r12':ach_r12,
                                                        'r13':ach_r13,
                                                        'r14':ach_r14,
                                                        'r':ach_r,
                                                        'c1':ach_c1,
                                                        'c2':ach_c2,
                                                        'c3':ach_c3,
                                                        'c4':ach_c4,
                                                        'c5':ach_c5,
                                                        'c6':ach_c6,
                                                        'c7':ach_c7,
                                                        'c8':ach_c8,
                                                        'c9':ach_c9,
                                                        'c10':ach_c10,
                                                        'c11':ach_c11,
                                                        'c12':ach_c12,
                                                        'c13':ach_c13,
                                                        'c14':ach_c14,
                                                        'c':ach_c,
                                                        'rs':ach_rs,
                                                        'percentile':percentile_ach,
                                                        'category':ach_category,
                                                        'description':epps_personality.description if epps_personality else False,
                                                    
                                                        }))
                
                def_answer = []
                def_answer_c = []
                def_r1 = 0
                def_r2 = 0
                def_r3 = 0
                def_r4 = 0
                def_r5 = 0
                def_r6 = 0
                def_r7 = 0
                def_r8 = 0
                def_r9 = 0
                def_r10 = 0
                def_r11 = 0
                def_r12 = 0
                def_r13 = 0
                def_r14 = 0
                def_r = 0
                
                def_c1 = 0
                def_c2 = 0
                def_c3 = 0
                def_c4 = 0
                def_c5 = 0
                def_c6 = 0
                def_c7 = 0
                def_c8 = 0
                def_c9 = 0
                def_c10 = 0
                def_c11 = 0
                def_c12 = 0
                def_c13 = 0
                def_c14 = 0
                def_c = 0
                
                def_rs = 0
                
                if no_2:
                    if no_2.suggested_answer_id.code == "a":
                        def_r1 = 1
                        def_answer.append(def_r1)
                if no_12:
                    if no_12.suggested_answer_id.code == "a":
                        def_r2 = 1
                        def_answer.append(def_r2)
                if no_17:
                    if no_17.suggested_answer_id.code == "a":
                        def_r3 = 1
                        def_answer.append(def_r3)
                if no_22:
                    if no_22.suggested_answer_id.code == "a":
                        def_r4 = 1
                        def_answer.append(def_r4)
                if no_27:
                    if no_27.suggested_answer_id.code == "a":
                        def_r5 = 1
                        def_answer.append(def_r5)
                if no_32:
                    if no_32.suggested_answer_id.code == "a":
                        def_r6 = 1
                        def_answer.append(def_r6)
                if no_37:
                    if no_37.suggested_answer_id.code == "a":
                        def_r7 = 1
                        def_answer.append(def_r7)
                if no_42:
                    if no_42.suggested_answer_id.code == "a":
                        def_r8 = 1
                        def_answer.append(def_r8)
                if no_47:
                    if no_47.suggested_answer_id.code == "a":
                        def_r9 = 1
                        def_answer.append(def_r9)
                if no_52:
                    if no_52.suggested_answer_id.code == "a":
                        def_r10 = 1
                        def_answer.append(def_r10)
                if no_57:
                    if no_57.suggested_answer_id.code == "a":
                        def_r11 = 1
                        def_answer.append(def_r11)
                if no_62:
                    if no_62.suggested_answer_id.code == "a":
                        def_r12 = 1
                        def_answer.append(def_r12)
                if no_67:
                    if no_67.suggested_answer_id.code == "a":
                        def_r13 = 1
                        def_answer.append(def_r13)
                if no_72:
                    if no_72.suggested_answer_id.code == "a":
                        def_r14 = 1
                        def_answer.append(def_r14)
                def_r = len(def_answer)
                
                if no_6:
                    if no_6.suggested_answer_id.code == "b":
                        def_c1 = 1
                        def_answer_c.append(def_c1)
                if no_8:
                    if no_8.suggested_answer_id.code == "b":
                        def_c2 = 1
                        def_answer_c.append(def_c2)
                if no_9:
                    if no_9.suggested_answer_id.code == "b":
                        def_c3 = 1
                        def_answer_c.append(def_c3)
                if no_10:
                    if no_10.suggested_answer_id.code == "b":
                        def_c4 = 1
                        def_answer_c.append(def_c4)
                if no_81:
                    if no_81.suggested_answer_id.code == "b":
                        def_c5 = 1
                        def_answer_c.append(def_c5)
                if no_82:
                    if no_82.suggested_answer_id.code == "b":
                        def_c6 = 1
                        def_answer_c.append(def_c6)
                if no_83:
                    if no_83.suggested_answer_id.code == "b":
                        def_c7 = 1
                        def_answer_c.append(def_c7)
                if no_84:
                    if no_84.suggested_answer_id.code == "b":
                        def_c8 = 1
                        def_answer_c.append(def_c8)
                if no_85:
                    if no_85.suggested_answer_id.code == "b":
                        def_c9 = 1
                        def_answer_c.append(def_c9)
                if no_156:
                    if no_156.suggested_answer_id.code == "b":
                        def_c10 = 1
                        def_answer_c.append(def_c10)
                if no_157:
                    if no_157.suggested_answer_id.code == "b":
                        def_c11 = 1
                        def_answer_c.append(def_c11)
                if no_158:
                    if no_158.suggested_answer_id.code == "b":
                        def_c12 = 1
                        def_answer_c.append(def_c12)
                if no_159:
                    if no_159.suggested_answer_id.code == "b":
                        def_c13 = 1
                        def_answer_c.append(def_c13)
                if no_160:
                    if no_160.suggested_answer_id.code == "b":
                        def_c14 = 1
                        def_answer_c.append(def_c14)
                def_c = len(def_answer_c)
                
                
                def_rs = def_r + def_c
                def_category = ""
                if scoring_matrix:
                        line_data_def = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == def_rs)
                        percentile_def = line_data_def.deference
                        def_category = self.epps_personality_category(percentile_def)
                        epps_personality_def =  self.env['survey.epps_personality'].search([('sequence','=',2)])
                        personality_ids.append((0,0,{
                                                    'factor':"def",
                                                    'r1':def_r1,
                                                        'r2':def_r2,
                                                        'r3':def_r3,
                                                        'r4':def_r4,
                                                        'r5':def_r5,
                                                        'r6':def_r6,
                                                        'r7':def_r7,
                                                        'r8':def_r8,
                                                        'r9':def_r9,
                                                        'r10':def_r10,
                                                        'r11':def_r11,
                                                        'r12':def_r12,
                                                        'r13':def_r13,
                                                        'r14':def_r14,
                                                        'r':def_r,
                                                        'c1':def_c1,
                                                        'c2':def_c2,
                                                        'c3':def_c3,
                                                        'c4':def_c4,
                                                        'c5':def_c5,
                                                        'c6':def_c6,
                                                        'c7':def_c7,
                                                        'c8':def_c8,
                                                        'c9':def_c9,
                                                        'c10':def_c10,
                                                        'c11':def_c11,
                                                        'c12':def_c12,
                                                        'c13':def_c13,
                                                        'c14':def_c14,
                                                        'c':def_c,
                                                        'rs':def_rs,
                                                        'percentile':percentile_def,
                                                        'category':def_category,
                                                        'description':epps_personality_def.description if epps_personality_def else False,
                                                        
                                                    
                                                        }))
                
                ord_answer_r = []
                ord_answer_c = []
                ord_r1 = 0
                ord_r2 = 0
                ord_r3 = 0
                ord_r4 = 0
                ord_r5 = 0
                ord_r6 = 0
                ord_r7 = 0
                ord_r8 = 0
                ord_r9 = 0
                ord_r10 = 0
                ord_r11 = 0
                ord_r12 = 0
                ord_r13 = 0
                ord_r14 = 0
                
                ord_r = 0
                ord_rs = 0
                
                
                ord_c1 = 0
                ord_c2 = 0
                ord_c3 = 0
                ord_c4 = 0
                ord_c5 = 0
                ord_c6 = 0
                ord_c7 = 0
                ord_c8 = 0
                ord_c9 = 0
                ord_c10 = 0
                ord_c11 = 0
                ord_c12 = 0
                ord_c13 = 0
                ord_c14 = 0
                
                ord_c = 0
                
                if no_3:
                    if no_3.suggested_answer_id.code == "a":
                        ord_r1 = 1
                        ord_answer_r.append(ord_r1)
                if no_8:
                    if no_8.suggested_answer_id.code == "a":
                        ord_r2 = 1
                        ord_answer_r.append(ord_r2)
                if no_18:
                    if no_18.suggested_answer_id.code == "a":
                        ord_r3 = 1
                        ord_answer_r.append(ord_r3)
                if no_23:
                    if no_23.suggested_answer_id.code == "a":
                        ord_r4 = 1
                        ord_answer_r.append(ord_r4)
                if no_28:
                    if no_28.suggested_answer_id.code == "a":
                        ord_r5 = 1
                        ord_answer_r.append(ord_r5)
                if no_33:
                    if no_33.suggested_answer_id.code == "a":
                        ord_r6 = 1
                        ord_answer_r.append(ord_r6)
                if no_38:
                    if no_38.suggested_answer_id.code == "a":
                        ord_r7 = 1
                        ord_answer_r.append(ord_r7)
                if no_43:
                    if no_43.suggested_answer_id.code == "a":
                        ord_r8 = 1
                        ord_answer_r.append(ord_r8)
                if no_48:
                    if no_48.suggested_answer_id.code == "a":
                        ord_r9 = 1
                        ord_answer_r.append(ord_r9)
                if no_53:
                    if no_53.suggested_answer_id.code == "a":
                        ord_r10 = 1
                        ord_answer_r.append(ord_r10)
                if no_58:
                    if no_58.suggested_answer_id.code == "a":
                        ord_r11 = 1
                        ord_answer_r.append(ord_r11)
                if no_63:
                    if no_63.suggested_answer_id.code == "a":
                        ord_r12 = 1
                        ord_answer_r.append(ord_r12)
                if no_68:
                    if no_68.suggested_answer_id.code == "a":
                        ord_r13 = 1
                        ord_answer_r.append(ord_r13)
                if no_73:
                    if no_73.suggested_answer_id.code == "a":
                        ord_r14 = 1
                        ord_answer_r.append(ord_r14)
                ord_r = len(ord_answer_r)
                
                
                
                if no_11:
                    if no_11.suggested_answer_id.code == "b":
                        ord_c1 = 1
                        ord_answer_c.append(ord_c1)
                if no_12:
                    if no_12.suggested_answer_id.code == "b":
                        ord_c2 = 1
                        ord_answer_c.append(ord_c2)
                if no_14:
                    if no_14.suggested_answer_id.code == "b":
                        ord_c3 = 1
                        ord_answer_c.append(ord_c3)
                if no_15:
                    if no_15.suggested_answer_id.code == "b":
                        ord_c4 = 1
                        ord_answer_c.append(ord_c4)
                if no_86:
                    if no_86.suggested_answer_id.code == "b":
                        ord_c5 = 1
                        ord_answer_c.append(ord_c5)
                if no_87:
                    if no_87.suggested_answer_id.code == "b":
                        ord_c6 = 1
                        ord_answer_c.append(ord_c6)
                if no_88:
                    if no_88.suggested_answer_id.code == "b":
                        ord_c7 = 1
                        ord_answer_c.append(ord_c7)
                if no_89:
                    if no_89.suggested_answer_id.code == "b":
                        ord_c8 = 1
                        ord_answer_c.append(ord_c8)
                if no_90:
                    if no_90.suggested_answer_id.code == "b":
                        ord_c9 = 1
                        ord_answer_c.append(ord_c9)
                if no_161:
                    if no_161.suggested_answer_id.code == "b":
                        ord_c10 = 1
                        ord_answer_c.append(ord_c10)
                if no_162:
                    if no_162.suggested_answer_id.code == "b":
                        ord_c11 = 1
                        ord_answer_c.append(ord_c11)
                if no_163:
                    if no_163.suggested_answer_id.code == "b":
                        ord_c12 = 1
                        ord_answer_c.append(ord_c12)
                if no_164:
                    if no_164.suggested_answer_id.code == "b":
                        ord_c13 = 1
                        ord_answer_c.append(ord_c13)
                if no_165:
                    if no_165.suggested_answer_id.code == "b":
                        ord_c14 = 1
                        ord_answer_c.append(ord_c14)
                ord_c = len(ord_answer_c)
                ord_rs = ord_r + ord_c
                
                
                ord_category = ""
                if scoring_matrix:
                        line_data_ord = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == ord_rs)
                        percentile_ord = line_data_ord.order
                        ord_category = self.epps_personality_category(percentile_ord)
                        epps_personality_ord =  self.env['survey.epps_personality'].search([('sequence','=',3)])
                        personality_ids.append((0,0,{
                                                    'factor':"ord",
                                                    'r1':ord_r1,
                                                        'r2':ord_r2,
                                                        'r3':ord_r3,
                                                        'r4':ord_r4,
                                                        'r5':ord_r5,
                                                        'r6':ord_r6,
                                                        'r7':ord_r7,
                                                        'r8':ord_r8,
                                                        'r9':ord_r9,
                                                        'r10':ord_r10,
                                                        'r11':ord_r11,
                                                        'r12':ord_r12,
                                                        'r13':ord_r13,
                                                        'r14':ord_r14,
                                                        'r':ord_r,
                                                        'c1':ord_c1,
                                                        'c2':ord_c2,
                                                        'c3':ord_c3,
                                                        'c4':ord_c4,
                                                        'c5':ord_c5,
                                                        'c6':ord_c6,
                                                        'c7':ord_c7,
                                                        'c8':ord_c8,
                                                        'c9':ord_c9,
                                                        'c10':ord_c10,
                                                        'c11':ord_c11,
                                                        'c12':ord_c12,
                                                        'c13':ord_c13,
                                                        'c14':ord_c14,
                                                        'c':ord_c,
                                                        'rs':ord_rs,
                                                        'percentile':percentile_ord,
                                                        'category':ord_category,
                                                        'description':epps_personality_ord.description if epps_personality_ord else False
                                                    
                                                        }))
                        
                
                exh_answer_r = []
                exh_answer_c = []
                exh_r1 = 0
                exh_r2 = 0
                exh_r3 = 0
                exh_r4 = 0
                exh_r5 = 0
                exh_r6 = 0
                exh_r7 = 0
                exh_r8 = 0
                exh_r9 = 0
                exh_r10 = 0
                exh_r11 = 0
                exh_r12 = 0
                exh_r13 = 0
                exh_r14 = 0
                exh_r = 0
                
                exh_c1 = 0
                exh_c2 = 0
                exh_c3 = 0
                exh_c4 = 0
                exh_c5 = 0
                exh_c6 = 0
                exh_c7 = 0
                exh_c8 = 0
                exh_c9 = 0
                exh_c10 = 0
                exh_c11 = 0
                exh_c12 = 0
                exh_c13 = 0
                exh_c14 = 0
                exh_c = 0
                
                exh_rs = 0
                
                
                if no_4:
                    if no_4.suggested_answer_id.code == "a":
                        exh_r1 = 1
                        exh_answer_r.append(exh_r1)
                if no_9:
                    if no_9.suggested_answer_id.code == "a":
                        exh_r2 = 1
                        exh_answer_r.append(exh_r2)
                if no_14:
                    if no_14.suggested_answer_id.code == "a":
                        exh_r3 = 1
                        exh_answer_r.append(exh_r3)
                if no_24:
                    if no_24.suggested_answer_id.code == "a":
                        exh_r4 = 1
                        exh_answer_r.append(exh_r4)
                if no_29:
                    if no_29.suggested_answer_id.code == "a":
                        exh_r5 = 1
                        exh_answer_r.append(exh_r5)
                if no_34:
                    if no_34.suggested_answer_id.code == "a":
                        exh_r6 = 1
                        exh_answer_r.append(exh_r6)
                if no_39:
                    if no_39.suggested_answer_id.code == "a":
                        exh_r7 = 1
                        exh_answer_r.append(exh_r7)
                if no_44:
                    if no_44.suggested_answer_id.code == "a":
                        exh_r8 = 1
                        exh_answer_r.append(exh_r8)
                if no_49:
                    if no_49.suggested_answer_id.code == "a":
                        exh_r9 = 1
                        exh_answer_r.append(exh_r9)
                if no_54:
                    if no_54.suggested_answer_id.code == "a":
                        exh_r10 = 1
                        exh_answer_r.append(exh_r10)
                if no_59:
                    if no_59.suggested_answer_id.code == "a":
                        exh_r11 = 1
                        exh_answer_r.append(exh_r11)
                if no_64:
                    if no_64.suggested_answer_id.code == "a":
                        exh_r12 = 1
                        exh_answer_r.append(exh_r12)
                if no_69:
                    if no_69.suggested_answer_id.code == "a":
                        exh_r13 = 1
                        exh_answer_r.append(exh_r13)
                if no_74:
                    if no_74.suggested_answer_id.code == "a":
                        exh_r14 = 1
                        exh_answer_r.append(exh_r14)
                        
                exh_r = len(exh_answer_r)
                
                if no_16:
                    if no_16.suggested_answer_id.code == "b":
                        exh_c1 = 1
                        exh_answer_c.append(exh_c1)
                if no_17:
                    if no_17.suggested_answer_id.code == "b":
                        exh_c2 = 1
                        exh_answer_c.append(exh_c2)
                if no_18:
                    if no_18.suggested_answer_id.code == "b":
                        exh_c3 = 1
                        exh_answer_c.append(exh_c3)
                if no_20:
                    if no_20.suggested_answer_id.code == "b":
                        exh_c4 = 1
                        exh_answer_c.append(exh_c4)
                if no_91:
                    if no_91.suggested_answer_id.code == "b":
                        exh_c5 = 1
                        exh_answer_c.append(exh_c5)
                if no_92:
                    if no_92.suggested_answer_id.code == "b":
                        exh_c6 = 1
                        exh_answer_c.append(exh_c6)
                if no_93:
                    if no_93.suggested_answer_id.code == "b":
                        exh_c7 = 1
                        exh_answer_c.append(exh_c7)
                if no_94:
                    if no_94.suggested_answer_id.code == "b":
                        exh_c8 = 1
                        exh_answer_c.append(exh_c8)
                if no_95:
                    if no_95.suggested_answer_id.code == "b":
                        exh_c9 = 1
                        exh_answer_c.append(exh_c9)
                if no_166:
                    if no_166.suggested_answer_id.code == "b":
                        exh_c10 = 1
                        exh_answer_c.append(exh_c10)
                if no_167:
                    if no_167.suggested_answer_id.code == "b":
                        exh_c11 = 1
                        exh_answer_c.append(exh_c11)
                if no_168:
                    if no_168.suggested_answer_id.code == "b":
                        exh_c12 = 1
                        exh_answer_c.append(exh_c12)
                if no_169:
                    if no_169.suggested_answer_id.code == "b":
                        exh_c13 = 1
                        exh_answer_c.append(exh_c13)
                if no_170:
                    if no_170.suggested_answer_id.code == "b":
                        exh_c14 = 1
                        exh_answer_c.append(exh_c14)
                exh_c = len(exh_answer_c)
                exh_rs = exh_r + exh_c
                
                
                exh_category = ""
                if scoring_matrix:
                        line_data_exh = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == exh_rs)
                        percentile_exh = line_data_exh.exhibition
                        exh_category = self.epps_personality_category(percentile_exh)
                        epps_personality_exh =  self.env['survey.epps_personality'].search([('sequence','=',4)])
                        personality_ids.append((0,0,{
                                                    'factor':"exh",
                                                    'r1':exh_r1,
                                                        'r2':exh_r2,
                                                        'r3':exh_r3,
                                                        'r4':exh_r4,
                                                        'r5':exh_r5,
                                                        'r6':exh_r6,
                                                        'r7':exh_r7,
                                                        'r8':exh_r8,
                                                        'r9':exh_r9,
                                                        'r10':exh_r10,
                                                        'r11':exh_r11,
                                                        'r12':exh_r12,
                                                        'r13':exh_r13,
                                                        'r14':exh_r14,
                                                        'r':exh_r,
                                                        'c1':exh_c1,
                                                        'c2':exh_c2,
                                                        'c3':exh_c3,
                                                        'c4':exh_c4,
                                                        'c5':exh_c5,
                                                        'c6':exh_c6,
                                                        'c7':exh_c7,
                                                        'c8':exh_c8,
                                                        'c9':exh_c9,
                                                        'c10':exh_c10,
                                                        'c11':exh_c11,
                                                        'c12':exh_c12,
                                                        'c13':exh_c13,
                                                        'c14':exh_c14,
                                                        'c':exh_c,
                                                        'rs':exh_rs,
                                                        'percentile':percentile_exh,
                                                        'category':exh_category,
                                                        'description':epps_personality_exh.description if epps_personality_exh else False
                                                    
                                                        }))             
                aut_answer_r = []
                aut_answer_c = []
                aut_r1 = 0
                aut_r2 = 0
                aut_r3 = 0
                aut_r4 = 0
                aut_r5 = 0
                aut_r6 = 0
                aut_r7 = 0
                aut_r8 = 0
                aut_r9 = 0
                aut_r10 = 0
                aut_r11 = 0
                aut_r12 = 0
                aut_r13 = 0
                aut_r14 = 0
                aut_r = 0
                
                aut_c1 = 0
                aut_c2 = 0
                aut_c3 = 0
                aut_c4 = 0
                aut_c5 = 0
                aut_c6 = 0
                aut_c7 = 0
                aut_c8 = 0
                aut_c9 = 0
                aut_c10 = 0
                aut_c11 = 0
                aut_c12 = 0
                aut_c13 = 0
                aut_c14 = 0
                aut_c = 0
                
                
                if no_5:
                    if no_5.suggested_answer_id.code == "a":
                        aut_r1 = 1
                        aut_answer_r.append(aut_r1)
                if no_10:
                    if no_10.suggested_answer_id.code == "a":
                        aut_r2 = 1
                        aut_answer_r.append(aut_r2)
                if no_15:
                    if no_15.suggested_answer_id.code == "a":
                        aut_r3 = 1
                        aut_answer_r.append(aut_r3)
                if no_20:
                    if no_20.suggested_answer_id.code == "a":
                        aut_r4 = 1
                        aut_answer_r.append(aut_r4)
                if no_30:
                    if no_30.suggested_answer_id.code == "a":
                        aut_r5 = 1
                        aut_answer_r.append(aut_r5)
                if no_35:
                    if no_35.suggested_answer_id.code == "a":
                        aut_r6 = 1
                        aut_answer_r.append(aut_r6)
                if no_40:
                    if no_40.suggested_answer_id.code == "a":
                        aut_r7 = 1
                        aut_answer_r.append(aut_r7)
                if no_45:
                    if no_45.suggested_answer_id.code == "a":
                        aut_r8 = 1
                        aut_answer_r.append(aut_r8)
                if no_50:
                    if no_50.suggested_answer_id.code == "a":
                        aut_r9 = 1
                        aut_answer_r.append(aut_r9)
                if no_55:
                    if no_55.suggested_answer_id.code == "a":
                        aut_r10 = 1
                        aut_answer_r.append(aut_r10)
                if no_60:
                    if no_60.suggested_answer_id.code == "a":
                        aut_r11 = 1
                        aut_answer_r.append(aut_r11)
                if no_65:
                    if no_65.suggested_answer_id.code == "a":
                        aut_r12 = 1
                        aut_answer_r.append(aut_r12)
                if no_70:
                    if no_70.suggested_answer_id.code == "a":
                        aut_r13 = 1
                        aut_answer_r.append(aut_r13)
                if no_75:
                    if no_75.suggested_answer_id.code == "a":
                        aut_r14 = 1
                        aut_answer_r.append(aut_r14)
                
                aut_r =len(aut_answer_r)
                
                if no_21:
                    if no_21.suggested_answer_id.code == "b":
                        aut_c1 = 1
                        aut_answer_c.append(aut_c1)
                if no_22:
                    if no_22.suggested_answer_id.code == "b":
                        aut_c2 = 1
                        aut_answer_c.append(aut_c2)
                if no_23:
                    if no_23.suggested_answer_id.code == "b":
                        aut_c3 = 1
                        aut_answer_c.append(aut_c3)
                if no_24:
                    if no_24.suggested_answer_id.code == "b":
                        aut_c4 = 1
                        aut_answer_c.append(aut_c4)
                if no_96:
                    if no_96.suggested_answer_id.code == "b":
                        aut_c5 = 1
                        aut_answer_c.append(aut_c5)
                if no_97:
                    if no_97.suggested_answer_id.code == "b":
                        aut_c6 = 1
                        aut_answer_c.append(aut_c6)
                if no_98:
                    if no_98.suggested_answer_id.code == "b":
                        aut_c7 = 1
                        aut_answer_c.append(aut_c7)
                if no_99:
                    if no_99.suggested_answer_id.code == "b":
                        aut_c8 = 1
                        aut_answer_c.append(aut_c8)
                if no_100:
                    if no_100.suggested_answer_id.code == "b":
                        aut_c9 = 1
                        aut_answer_c.append(aut_c9)
                if no_171:
                    if no_171.suggested_answer_id.code == "b":
                        aut_c10 = 1
                        aut_answer_c.append(aut_c10)
                if no_172:
                    if no_172.suggested_answer_id.code == "b":
                        aut_c11 = 1
                        aut_answer_c.append(aut_c11)
                if no_173:
                    if no_173.suggested_answer_id.code == "b":
                        aut_c12 = 1
                        aut_answer_c.append(aut_c12)
                if no_174:
                    if no_174.suggested_answer_id.code == "b":
                        aut_c13 = 1
                        aut_answer_c.append(aut_c13)
                if no_175:
                    if no_175.suggested_answer_id.code == "b":
                        aut_c14 = 1
                        aut_answer_c.append(aut_c14)
                aut_c = len(aut_answer_c)
                
                aut_rs = aut_r + aut_c
                
                
                aut_category = ""
                if scoring_matrix:
                        line_data_aut = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == aut_rs)
                        percentile_aut = line_data_aut.autonomy
                        aut_category = self.epps_personality_category(percentile_aut)
                        epps_personality_aut =  self.env['survey.epps_personality'].search([('sequence','=',5)])
                        personality_ids.append((0,0,{
                                                    'factor':"aut",
                                                    'r1':aut_r1,
                                                        'r2':aut_r2,
                                                        'r3':aut_r3,
                                                        'r4':aut_r4,
                                                        'r5':aut_r5,
                                                        'r6':aut_r6,
                                                        'r7':aut_r7,
                                                        'r8':aut_r8,
                                                        'r9':aut_r9,
                                                        'r10':aut_r10,
                                                        'r11':aut_r11,
                                                        'r12':aut_r12,
                                                        'r13':aut_r13,
                                                        'r14':aut_r14,
                                                        'r':aut_r,
                                                        'c1':aut_c1,
                                                        'c2':aut_c2,
                                                        'c3':aut_c3,
                                                        'c4':aut_c4,
                                                        'c5':aut_c5,
                                                        'c6':aut_c6,
                                                        'c7':aut_c7,
                                                        'c8':aut_c8,
                                                        'c9':aut_c9,
                                                        'c10':aut_c10,
                                                        'c11':aut_c11,
                                                        'c12':aut_c12,
                                                        'c13':aut_c13,
                                                        'c14':aut_c14,
                                                        'c':aut_c,
                                                        'rs':aut_rs,
                                                        'percentile':percentile_aut,
                                                        'category':aut_category,
                                                        'description':epps_personality_aut.description if epps_personality_aut else False
                                                    
                                                        }))
                        
                        
                
                
                
                
                aff_answer_r = []
                aff_answer_c = []
                aff_r1 = 0
                aff_r2 = 0
                aff_r3 = 0
                aff_r4 = 0
                aff_r5 = 0
                aff_r6 = 0
                aff_r7 = 0
                aff_r8 = 0
                aff_r9 = 0
                aff_r10 = 0
                aff_r11 = 0
                aff_r12 = 0
                aff_r13 = 0
                aff_r14 = 0
                aff_r = 0
                
                aff_c1 = 0
                aff_c2 = 0
                aff_c3 = 0
                aff_c4 = 0
                aff_c5 = 0
                aff_c6 = 0
                aff_c7 = 0
                aff_c8 = 0
                aff_c9 = 0
                aff_c10 = 0
                aff_c11 = 0
                aff_c12 = 0
                aff_c13 = 0
                aff_c14 = 0
                aff_c = 0
                
                
                if no_76:
                    if no_76.suggested_answer_id.code == "a":
                        aff_r1 = 1
                        aff_answer_r.append(aff_r1)
                if no_81:
                    if no_81.suggested_answer_id.code == "a":
                        aff_r2 = 1
                        aff_answer_r.append(aff_r2)
                if no_86:
                    if no_86.suggested_answer_id.code == "a":
                        aff_r3 = 1
                        aff_answer_r.append(aff_r3)
                if no_91:
                    if no_91.suggested_answer_id.code == "a":
                        aff_r4 = 1
                        aff_answer_r.append(aff_r4)
                if no_96:
                    if no_96.suggested_answer_id.code == "a":
                        aff_r5 = 1
                        aff_answer_r.append(aff_r5)
                if no_106:
                    if no_106.suggested_answer_id.code == "a":
                        aff_r6 = 1
                        aff_answer_r.append(aff_r6)
                if no_111:
                    if no_111.suggested_answer_id.code == "a":
                        aff_r7 = 1
                        aff_answer_r.append(aff_r7)
                if no_116:
                    if no_116.suggested_answer_id.code == "a":
                        aff_r8 = 1
                        aff_answer_r.append(aff_r8)
                if no_121:
                    if no_121.suggested_answer_id.code == "a":
                        aff_r9 = 1
                        aff_answer_r.append(aff_r9)
                if no_126:
                    if no_126.suggested_answer_id.code == "a":
                        aff_r10 = 1
                        aff_answer_r.append(aff_r10)
                if no_131:
                    if no_131.suggested_answer_id.code == "a":
                        aff_r11 = 1
                        aff_answer_r.append(aff_r11)
                if no_136:
                    if no_136.suggested_answer_id.code == "a":
                        aff_r12 = 1
                        aff_answer_r.append(aff_r12)
                if no_141:
                    if no_141.suggested_answer_id.code == "a":
                        aff_r13 = 1
                        aff_answer_r.append(aff_r13)
                if no_146:
                    if no_146.suggested_answer_id.code == "a":
                        aff_r14 = 1
                        aff_answer_r.append(aff_r14)
                
                
                aff_r =len(aff_answer_r)
                
                if no_26:
                    if no_26.suggested_answer_id.code == "b":
                        aff_c1 = 1
                        aff_answer_c.append(aff_c1)
                if no_26:
                    if no_26.suggested_answer_id.code == "b":
                        aff_c2 = 1
                        aff_answer_c.append(aff_c2)
                if no_28:
                    if no_28.suggested_answer_id.code == "b":
                        aff_c3 = 1
                        aff_answer_c.append(aff_c3)
                if no_29:
                    if no_29.suggested_answer_id.code == "b":
                        aff_c4 = 1
                        aff_answer_c.append(aff_c4)
                if no_30:
                    if no_30.suggested_answer_id.code == "b":
                        aff_c5 = 1
                        aff_answer_c.append(aff_c5)
                if no_102:
                    if no_102.suggested_answer_id.code == "b":
                        aff_c6 = 1
                        aff_answer_c.append(aff_c6)
                if no_103:
                    if no_103.suggested_answer_id.code == "b":
                        aff_c7 = 1
                        aff_answer_c.append(aff_c7)
                if no_104:
                    if no_104.suggested_answer_id.code == "b":
                        aff_c8 = 1
                        aff_answer_c.append(aff_c8)
                if no_105:
                    if no_105.suggested_answer_id.code == "b":
                        aff_c9 = 1
                        aff_answer_c.append(aff_c9)
                if no_176:
                    if no_176.suggested_answer_id.code == "b":
                        aff_c10 = 1
                        aff_answer_c.append(aff_c10)
                if no_177:
                    if no_177.suggested_answer_id.code == "b":
                        aff_c11 = 1
                        aff_answer_c.append(aff_c11)
                if no_178:
                    if no_178.suggested_answer_id.code == "b":
                        aff_c12 = 1
                        aff_answer_c.append(aff_c12)
                if no_179:
                    if no_179.suggested_answer_id.code == "b":
                        aff_c13 = 1
                        aff_answer_c.append(aff_c13)
                if no_180:
                    if no_180.suggested_answer_id.code == "b":
                        aff_c14 = 1
                        aff_answer_c.append(aff_c14)
                aff_c = len(aff_answer_c)
                
                aff_rs = aff_r + aff_c
                
                
                aff_category = ""
                if scoring_matrix:
                        line_data_aff = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == aff_rs)
                        percentile_aff = line_data_aff.affiliation
                        aff_category = self.epps_personality_category(percentile_aff)
                        epps_personality_aff =  self.env['survey.epps_personality'].search([('sequence','=',6)])
                        personality_ids.append((0,0,{
                                                    'factor':"aff",
                                                    'r1':aff_r1,
                                                        'r2':aff_r2,
                                                        'r3':aff_r3,
                                                        'r4':aff_r4,
                                                        'r5':aff_r5,
                                                        'r6':aff_r6,
                                                        'r7':aff_r7,
                                                        'r8':aff_r8,
                                                        'r9':aff_r9,
                                                        'r10':aff_r10,
                                                        'r11':aff_r11,
                                                        'r12':aff_r12,
                                                        'r13':aff_r13,
                                                        'r14':aff_r14,
                                                        'r':aff_r,
                                                        'c1':aff_c1,
                                                        'c2':aff_c2,
                                                        'c3':aff_c3,
                                                        'c4':aff_c4,
                                                        'c5':aff_c5,
                                                        'c6':aff_c6,
                                                        'c7':aff_c7,
                                                        'c8':aff_c8,
                                                        'c9':aff_c9,
                                                        'c10':aff_c10,
                                                        'c11':aff_c11,
                                                        'c12':aff_c12,
                                                        'c13':aff_c13,
                                                        'c14':aff_c14,
                                                        'c':aff_c,
                                                        'rs':aff_rs,
                                                        'percentile':percentile_aff,
                                                        'category':aff_category,
                                                        'description':epps_personality_aff.description if epps_personality_aff else False
                                                    
                                                        }))
                
                
                
                int_answer_r = []
                int_answer_c = []
                int_r1 = 0
                int_r2 = 0
                int_r3 = 0
                int_r4 = 0
                int_r5 = 0
                int_r6 = 0
                int_r7 = 0
                int_r8 = 0
                int_r9 = 0
                int_r10 = 0
                int_r11 = 0
                int_r12 = 0
                int_r13 = 0
                int_r14 = 0
                int_r = 0
                
                int_c1 = 0
                int_c2 = 0
                int_c3 = 0
                int_c4 = 0
                int_c5 = 0
                int_c6 = 0
                int_c7 = 0
                int_c8 = 0
                int_c9 = 0
                int_c10 = 0
                int_c11 = 0
                int_c12 = 0
                int_c13 = 0
                int_c14 = 0
                int_c = 0
                
                
                if no_77:
                    if no_77.suggested_answer_id.code == "a":
                        int_r1 = 1
                        int_answer_r.append(int_r1)
                if no_82:
                    if no_82.suggested_answer_id.code == "a":
                        int_r2 = 1
                        int_answer_r.append(int_r2)
                if no_87:
                    if no_87.suggested_answer_id.code == "a":
                        int_r3 = 1
                        int_answer_r.append(int_r3)
                if no_92:
                    if no_92.suggested_answer_id.code == "a":
                        int_r4 = 1
                        int_answer_r.append(int_r4)
                if no_97:
                    if no_97.suggested_answer_id.code == "a":
                        int_r5 = 1
                        int_answer_r.append(int_r5)
                if no_102:
                    if no_102.suggested_answer_id.code == "a":
                        int_r6 = 1
                        int_answer_r.append(int_r6)
                if no_112:
                    if no_112.suggested_answer_id.code == "a":
                        aff_r7 = 1
                        int_answer_r.append(aff_r7)
                if no_117:
                    if no_117.suggested_answer_id.code == "a":
                        int_r8 = 1
                        int_answer_r.append(int_r8)
                if no_122:
                    if no_122.suggested_answer_id.code == "a":
                        int_r9 = 1
                        int_answer_r.append(int_r9)
                if no_127:
                    if no_127.suggested_answer_id.code == "a":
                        int_r10 = 1
                        int_answer_r.append(int_r10)
                if no_132:
                    if no_132.suggested_answer_id.code == "a":
                        int_r11 = 1
                        int_answer_r.append(int_r11)
                if no_137:
                    if no_137.suggested_answer_id.code == "a":
                        int_r12 = 1
                        int_answer_r.append(int_r12)
                if no_142:
                    if no_142.suggested_answer_id.code == "a":
                        int_r13 = 1
                        int_answer_r.append(int_r13)
                if no_147:
                    if no_147.suggested_answer_id.code == "a":
                        int_r14 = 1
                        int_answer_r.append(int_r14)
                
                
                int_r =len(int_answer_r)
                
                if no_31:
                    if no_31.suggested_answer_id.code == "b":
                        int_c1 = 1
                        int_answer_c.append(int_c1)
                if no_32:
                    if no_32.suggested_answer_id.code == "b":
                        int_c2 = 1
                        int_answer_c.append(int_c2)
                if no_33:
                    if no_33.suggested_answer_id.code == "b":
                        int_c3 = 1
                        int_answer_c.append(int_c3)
                if no_34:
                    if no_34.suggested_answer_id.code == "b":
                        int_c4 = 1
                        int_answer_c.append(int_c4)
                if no_35:
                    if no_35.suggested_answer_id.code == "b":
                        int_c5 = 1
                        int_answer_c.append(int_c5)
                if no_106:
                    if no_106.suggested_answer_id.code == "b":
                        int_c6 = 1
                        int_answer_c.append(int_c6)
                if no_108:
                    if no_108.suggested_answer_id.code == "b":
                        int_c7 = 1
                        int_answer_c.append(int_c7)
                if no_109:
                    if no_109.suggested_answer_id.code == "b":
                        int_c8 = 1
                        int_answer_c.append(int_c8)
                if no_110:
                    if no_110.suggested_answer_id.code == "b":
                        int_c9 = 1
                        int_answer_c.append(int_c9)
                if no_181:
                    if no_181.suggested_answer_id.code == "b":
                        int_c10 = 1
                        int_answer_c.append(int_c10)
                if no_182:
                    if no_182.suggested_answer_id.code == "b":
                        int_c11 = 1
                        int_answer_c.append(int_c11)
                if no_183:
                    if no_183.suggested_answer_id.code == "b":
                        int_c12 = 1
                        int_answer_c.append(int_c12)
                if no_184:
                    if no_184.suggested_answer_id.code == "b":
                        int_c13 = 1
                        int_answer_c.append(int_c13)
                if no_185:
                    if no_185.suggested_answer_id.code == "b":
                        int_c14 = 1
                        int_answer_c.append(int_c14)
                int_c = len(int_answer_c)
                
                int_rs = int_r + int_c
                
                
                int_category = ""
                if scoring_matrix:
                        line_data_int = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == int_rs)
                        percentile_int = line_data_int.intraception
                        int_category = self.epps_personality_category(percentile_int)
                        epps_personality_int =  self.env['survey.epps_personality'].search([('sequence','=',7)])
                        personality_ids.append((0,0,{
                                                    'factor':"int",
                                                    'r1':int_r1,
                                                        'r2':int_r2,
                                                        'r3':int_r3,
                                                        'r4':int_r4,
                                                        'r5':int_r5,
                                                        'r6':int_r6,
                                                        'r7':int_r7,
                                                        'r8':int_r8,
                                                        'r9':int_r9,
                                                        'r10':int_r10,
                                                        'r11':int_r11,
                                                        'r12':int_r12,
                                                        'r13':int_r13,
                                                        'r14':int_r14,
                                                        'r':int_r,
                                                        'c1':int_c1,
                                                        'c2':int_c2,
                                                        'c3':int_c3,
                                                        'c4':int_c4,
                                                        'c5':int_c5,
                                                        'c6':int_c6,
                                                        'c7':int_c7,
                                                        'c8':int_c8,
                                                        'c9':int_c9,
                                                        'c10':int_c10,
                                                        'c11':int_c11,
                                                        'c12':int_c12,
                                                        'c13':int_c13,
                                                        'c14':int_c14,
                                                        'c':int_c,
                                                        'rs':int_rs,
                                                        'percentile':percentile_int,
                                                        'category':int_category,
                                                        'description':epps_personality_int.description if epps_personality_int else False
                                                    
                                                        }))
                
                
                
                suc_answer_r = []
                suc_answer_c = []
                suc_r1 = 0
                suc_r2 = 0
                suc_r3 = 0
                suc_r4 = 0
                suc_r5 = 0
                suc_r6 = 0
                suc_r7 = 0
                suc_r8 = 0
                suc_r9 = 0
                suc_r10 = 0
                suc_r11 = 0
                suc_r12 = 0
                suc_r13 = 0
                suc_r14 = 0
                suc_r = 0
                
                suc_c1 = 0
                suc_c2 = 0
                suc_c3 = 0
                suc_c4 = 0
                suc_c5 = 0
                suc_c6 = 0
                suc_c7 = 0
                suc_c8 = 0
                suc_c9 = 0
                suc_c10 = 0
                suc_c11 = 0
                suc_c12 = 0
                suc_c13 = 0
                suc_c14 = 0
                suc_c = 0
                
                
                if no_78:
                    if no_78.suggested_answer_id.code == "a":
                        suc_r1 = 1
                        suc_answer_r.append(suc_r1)
                if no_83:
                    if no_83.suggested_answer_id.code == "a":
                        suc_r2 = 1
                        suc_answer_r.append(suc_r2)
                if no_88:
                    if no_88.suggested_answer_id.code == "a":
                        suc_r3 = 1
                        suc_answer_r.append(suc_r3)
                if no_93:
                    if no_93.suggested_answer_id.code == "a":
                        suc_r4 = 1
                        suc_answer_r.append(suc_r4)
                if no_98:
                    if no_98.suggested_answer_id.code == "a":
                        suc_r5 = 1
                        suc_answer_r.append(suc_r5)
                if no_103:
                    if no_103.suggested_answer_id.code == "a":
                        suc_r6 = 1
                        suc_answer_r.append(suc_r6)
                if no_108:
                    if no_108.suggested_answer_id.code == "a":
                        suc_r7 = 1
                        suc_answer_r.append(suc_r7)
                if no_118:
                    if no_118.suggested_answer_id.code == "a":
                        suc_r8 = 1
                        suc_answer_r.append(suc_r8)
                if no_123:
                    if no_123.suggested_answer_id.code == "a":
                        suc_r9 = 1
                        suc_answer_r.append(suc_r9)
                if no_128:
                    if no_128.suggested_answer_id.code == "a":
                        suc_r10 = 1
                        suc_answer_r.append(suc_r10)
                if no_133:
                    if no_133.suggested_answer_id.code == "a":
                        suc_r11 = 1
                        suc_answer_r.append(suc_r11)
                if no_138:
                    if no_138.suggested_answer_id.code == "a":
                        suc_r12 = 1
                        suc_answer_r.append(suc_r12)
                if no_143:
                    if no_143.suggested_answer_id.code == "a":
                        suc_r13 = 1
                        suc_answer_r.append(suc_r13)
                if no_148:
                    if no_148.suggested_answer_id.code == "a":
                        suc_r14 = 1
                        suc_answer_r.append(suc_r14)
                
                
                suc_r =len(suc_answer_r)
                
                if no_36:
                    if no_36.suggested_answer_id.code == "b":
                        suc_c1 = 1
                        suc_answer_c.append(suc_c1)
                if no_37:
                    if no_37.suggested_answer_id.code == "b":
                        suc_c2 = 1
                        suc_answer_c.append(suc_c2)
                if no_38:
                    if no_38.suggested_answer_id.code == "b":
                        suc_c3 = 1
                        suc_answer_c.append(suc_c3)
                if no_39:
                    if no_39.suggested_answer_id.code == "b":
                        suc_c4 = 1
                        suc_answer_c.append(suc_c4)
                if no_40:
                    if no_40.suggested_answer_id.code == "b":
                        suc_c5 = 1
                        suc_answer_c.append(suc_c5)
                if no_111:
                    if no_111.suggested_answer_id.code == "b":
                        suc_c6 = 1
                        suc_answer_c.append(suc_c6)
                if no_112:
                    if no_112.suggested_answer_id.code == "b":
                        suc_c7 = 1
                        suc_answer_c.append(suc_c7)
                if no_114:
                    if no_114.suggested_answer_id.code == "b":
                        suc_c8 = 1
                        suc_answer_c.append(suc_c8)
                if no_115:
                    if no_115.suggested_answer_id.code == "b":
                        suc_c9 = 1
                        suc_answer_c.append(suc_c9)
                if no_186:
                    if no_186.suggested_answer_id.code == "b":
                        suc_c10 = 1
                        suc_answer_c.append(suc_c10)
                if no_187:
                    if no_187.suggested_answer_id.code == "b":
                        suc_c11 = 1
                        suc_answer_c.append(suc_c11)
                if no_188:
                    if no_188.suggested_answer_id.code == "b":
                        suc_c12 = 1
                        suc_answer_c.append(suc_c12)
                if no_189:
                    if no_189.suggested_answer_id.code == "b":
                        suc_c13 = 1
                        suc_answer_c.append(suc_c13)
                if no_190:
                    if no_190.suggested_answer_id.code == "b":
                        suc_c14 = 1
                        suc_answer_c.append(suc_c14)
                suc_c = len(suc_answer_c)
                
                suc_rs = suc_r + suc_c
                
                
                suc_category = ""
                if scoring_matrix:
                        line_data_suc = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == suc_rs)
                        percentile_suc = line_data_suc.succorance
                        suc_category = self.epps_personality_category(percentile_suc)
                        epps_personality_suc =  self.env['survey.epps_personality'].search([('sequence','=',8)])
                        personality_ids.append((0,0,{
                                                    'factor':"suc",
                                                    'r1':suc_r1,
                                                        'r2':suc_r2,
                                                        'r3':suc_r3,
                                                        'r4':suc_r4,
                                                        'r5':suc_r5,
                                                        'r6':suc_r6,
                                                        'r7':suc_r7,
                                                        'r8':suc_r8,
                                                        'r9':suc_r9,
                                                        'r10':suc_r10,
                                                        'r11':suc_r11,
                                                        'r12':suc_r12,
                                                        'r13':suc_r13,
                                                        'r14':suc_r14,
                                                        'r':suc_r,
                                                        'c1':suc_c1,
                                                        'c2':suc_c2,
                                                        'c3':suc_c3,
                                                        'c4':suc_c4,
                                                        'c5':suc_c5,
                                                        'c6':suc_c6,
                                                        'c7':suc_c7,
                                                        'c8':suc_c8,
                                                        'c9':suc_c9,
                                                        'c10':suc_c10,
                                                        'c11':suc_c11,
                                                        'c12':suc_c12,
                                                        'c13':suc_c13,
                                                        'c14':suc_c14,
                                                        'c':suc_c,
                                                        'rs':suc_rs,
                                                        'percentile':percentile_suc,
                                                        'category':suc_category,
                                                        'description':epps_personality_suc.description if epps_personality_suc else False
                                                    
                                                        }))
                
                
                
                dom_answer_r = []
                dom_answer_c = []
                dom_r1 = 0
                dom_r2 = 0
                dom_r3 = 0
                dom_r4 = 0
                dom_r5 = 0
                dom_r6 = 0
                dom_r7 = 0
                dom_r8 = 0
                dom_r9 = 0
                dom_r10 = 0
                dom_r11 = 0
                dom_r12 = 0
                dom_r13 = 0
                dom_r14 = 0
                dom_r = 0
                
                dom_c1 = 0
                dom_c2 = 0
                dom_c3 = 0
                dom_c4 = 0
                dom_c5 = 0
                dom_c6 = 0
                dom_c7 = 0
                dom_c8 = 0
                dom_c9 = 0
                dom_c10 = 0
                dom_c11 = 0
                dom_c12 = 0
                dom_c13 = 0
                dom_c14 = 0
                dom_c = 0
                
                
                if no_79:
                    if no_79.suggested_answer_id.code == "a":
                        dom_r1 = 1
                        dom_answer_r.append(dom_r1)
                if no_84:
                    if no_84.suggested_answer_id.code == "a":
                        dom_r2 = 1
                        dom_answer_r.append(dom_r2)
                if no_89:
                    if no_89.suggested_answer_id.code == "a":
                        dom_r3 = 1
                        dom_answer_r.append(dom_r3)
                if no_94:
                    if no_94.suggested_answer_id.code == "a":
                        dom_r4 = 1
                        dom_answer_r.append(dom_r4)
                if no_99:
                    if no_99.suggested_answer_id.code == "a":
                        dom_r5 = 1
                        dom_answer_r.append(dom_r5)
                if no_104:
                    if no_104.suggested_answer_id.code == "a":
                        dom_r6 = 1
                        dom_answer_r.append(dom_r6)
                if no_109:
                    if no_109.suggested_answer_id.code == "a":
                        dom_r7 = 1
                        dom_answer_r.append(dom_r7)
                if no_114:
                    if no_114.suggested_answer_id.code == "a":
                        dom_r8 = 1
                        dom_answer_r.append(dom_r8)
                if no_124:
                    if no_124.suggested_answer_id.code == "a":
                        dom_r9 = 1
                        dom_answer_r.append(dom_r9)
                if no_129:
                    if no_129.suggested_answer_id.code == "a":
                        dom_r10 = 1
                        dom_answer_r.append(dom_r10)
                if no_134:
                    if no_134.suggested_answer_id.code == "a":
                        dom_r11 = 1
                        dom_answer_r.append(dom_r11)
                if no_139:
                    if no_139.suggested_answer_id.code == "a":
                        dom_r12 = 1
                        dom_answer_r.append(dom_r12)
                if no_144:
                    if no_144.suggested_answer_id.code == "a":
                        dom_r13 = 1
                        dom_answer_r.append(dom_r13)
                if no_149:
                    if no_149.suggested_answer_id.code == "a":
                        dom_r14 = 1
                        dom_answer_r.append(dom_r14)
                
                
                dom_r =len(dom_answer_r)
                
                if no_41:
                    if no_41.suggested_answer_id.code == "b":
                        dom_c1 = 1
                        dom_answer_c.append(dom_c1)
                if no_42:
                    if no_42.suggested_answer_id.code == "b":
                        dom_c2 = 1
                        dom_answer_c.append(dom_c2)
                if no_43:
                    if no_43.suggested_answer_id.code == "b":
                        dom_c3 = 1
                        dom_answer_c.append(dom_c3)
                if no_44:
                    if no_44.suggested_answer_id.code == "b":
                        dom_c4 = 1
                        dom_answer_c.append(dom_c4)
                if no_45:
                    if no_45.suggested_answer_id.code == "b":
                        dom_c5 = 1
                        dom_answer_c.append(dom_c5)
                if no_116:
                    if no_116.suggested_answer_id.code == "b":
                        dom_c6 = 1
                        dom_answer_c.append(dom_c6)
                if no_117:
                    if no_117.suggested_answer_id.code == "b":
                        dom_c7 = 1
                        dom_answer_c.append(dom_c7)
                if no_118:
                    if no_118.suggested_answer_id.code == "b":
                        dom_c8 = 1
                        dom_answer_c.append(dom_c8)
                if no_120:
                    if no_120.suggested_answer_id.code == "b":
                        dom_c9 = 1
                        dom_answer_c.append(dom_c9)
                if no_191:
                    if no_191.suggested_answer_id.code == "b":
                        dom_c10 = 1
                        dom_answer_c.append(dom_c10)
                if no_192:
                    if no_192.suggested_answer_id.code == "b":
                        dom_c11 = 1
                        dom_answer_c.append(dom_c11)
                if no_193:
                    if no_193.suggested_answer_id.code == "b":
                        dom_c12 = 1
                        dom_answer_c.append(dom_c12)
                if no_194:
                    if no_194.suggested_answer_id.code == "b":
                        dom_c13 = 1
                        dom_answer_c.append(dom_c13)
                if no_195:
                    if no_195.suggested_answer_id.code == "b":
                        dom_c14 = 1
                        dom_answer_c.append(dom_c14)
                dom_c = len(dom_answer_c)
                
                dom_rs = dom_r + dom_c
                
                
                dom_category = ""
                if scoring_matrix:
                        line_data_dom = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == dom_rs)
                        percentile_dom = line_data_dom.dominance
                        dom_category = self.epps_personality_category(percentile_dom)
                        epps_personality_dom =  self.env['survey.epps_personality'].search([('sequence','=',9)])
                        personality_ids.append((0,0,{
                                                    'factor':"dom",
                                                    'r1':dom_r1,
                                                        'r2':dom_r2,
                                                        'r3':dom_r3,
                                                        'r4':dom_r4,
                                                        'r5':dom_r5,
                                                        'r6':dom_r6,
                                                        'r7':dom_r7,
                                                        'r8':dom_r8,
                                                        'r9':dom_r9,
                                                        'r10':dom_r10,
                                                        'r11':dom_r11,
                                                        'r12':dom_r12,
                                                        'r13':dom_r13,
                                                        'r14':dom_r14,
                                                        'r':dom_r,
                                                        'c1':dom_c1,
                                                        'c2':dom_c2,
                                                        'c3':dom_c3,
                                                        'c4':dom_c4,
                                                        'c5':dom_c5,
                                                        'c6':dom_c6,
                                                        'c7':dom_c7,
                                                        'c8':dom_c8,
                                                        'c9':dom_c9,
                                                        'c10':dom_c10,
                                                        'c11':dom_c11,
                                                        'c12':dom_c12,
                                                        'c13':dom_c13,
                                                        'c14':dom_c14,
                                                        'c':dom_c,
                                                        'rs':dom_rs,
                                                        'percentile':percentile_dom,
                                                        'category':dom_category,
                                                        'description':epps_personality_dom.description if epps_personality_dom else False
                                                    
                                                        }))
                
                
                
                
                aba_answer_r = []
                aba_answer_c = []
                aba_r1 = 0
                aba_r2 = 0
                aba_r3 = 0
                aba_r4 = 0
                aba_r5 = 0
                aba_r6 = 0
                aba_r7 = 0
                aba_r8 = 0
                aba_r9 = 0
                aba_r10 = 0
                aba_r11 = 0
                aba_r12 = 0
                aba_r13 = 0
                aba_r14 = 0
                aba_r = 0
                
                aba_c1 = 0
                aba_c2 = 0
                aba_c3 = 0
                aba_c4 = 0
                aba_c5 = 0
                aba_c6 = 0
                aba_c7 = 0
                aba_c8 = 0
                aba_c9 = 0
                aba_c10 = 0
                aba_c11 = 0
                aba_c12 = 0
                aba_c13 = 0
                aba_c14 = 0
                aba_c = 0
                
                
                if no_80:
                    if no_80.suggested_answer_id.code == "a":
                        aba_r1 = 1
                        aba_answer_r.append(aba_r1)
                if no_85:
                    if no_85.suggested_answer_id.code == "a":
                        aba_r2 = 1
                        aba_answer_r.append(aba_r2)
                if no_90:
                    if no_90.suggested_answer_id.code == "a":
                        aba_r3 = 1
                        aba_answer_r.append(aba_r3)
                if no_95:
                    if no_95.suggested_answer_id.code == "a":
                        aba_r4 = 1
                        aba_answer_r.append(aba_r4)
                if no_100:
                    if no_100.suggested_answer_id.code == "a":
                        aba_r5 = 1
                        aba_answer_r.append(aba_r5)
                if no_105:
                    if no_105.suggested_answer_id.code == "a":
                        aba_r6 = 1
                        aba_answer_r.append(aba_r6)
                if no_110:
                    if no_110.suggested_answer_id.code == "a":
                        aba_r7 = 1
                        aba_answer_r.append(aba_r7)
                if no_115:
                    if no_115.suggested_answer_id.code == "a":
                        aba_r8 = 1
                        aba_answer_r.append(aba_r8)
                if no_125:
                    if no_125.suggested_answer_id.code == "a":
                        aba_r9 = 1
                        aba_answer_r.append(aba_r9)
                if no_130:
                    if no_130.suggested_answer_id.code == "a":
                        aba_r10 = 1
                        aba_answer_r.append(aba_r10)
                if no_135:
                    if no_135.suggested_answer_id.code == "a":
                        aba_r11 = 1
                        aba_answer_r.append(aba_r11)
                if no_140:
                    if no_140.suggested_answer_id.code == "a":
                        aba_r12 = 1
                        aba_answer_r.append(aba_r12)
                if no_145:
                    if no_145.suggested_answer_id.code == "a":
                        aba_r13 = 1
                        aba_answer_r.append(aba_r13)
                if no_150:
                    if no_150.suggested_answer_id.code == "a":
                        aba_r14 = 1
                        aba_answer_r.append(aba_r14)
                
                
                aba_r = len(aba_answer_r)
                
                if no_46:
                    if no_46.suggested_answer_id.code == "b":
                        aba_c1 = 1
                        aba_answer_c.append(aba_c1)
                if no_47:
                    if no_47.suggested_answer_id.code == "b":
                        aba_c2 = 1
                        aba_answer_c.append(aba_c2)
                if no_48:
                    if no_48.suggested_answer_id.code == "b":
                        aba_c3 = 1
                        aba_answer_c.append(aba_c3)
                if no_49:
                    if no_49.suggested_answer_id.code == "b":
                        aba_c4 = 1
                        aba_answer_c.append(aba_c4)
                if no_50:
                    if no_50.suggested_answer_id.code == "b":
                        aba_c5 = 1
                        aba_answer_c.append(aba_c5)
                if no_121:
                    if no_121.suggested_answer_id.code == "b":
                        aba_c6 = 1
                        aba_answer_c.append(aba_c6)
                if no_122:
                    if no_122.suggested_answer_id.code == "b":
                        aba_c7 = 1
                        aba_answer_c.append(aba_c7)
                if no_123:
                    if no_123.suggested_answer_id.code == "b":
                        aba_c8 = 1
                        aba_answer_c.append(aba_c8)
                if no_124:
                    if no_124.suggested_answer_id.code == "b":
                        aba_c9 = 1
                        aba_answer_c.append(aba_c9)
                if no_196:
                    if no_196.suggested_answer_id.code == "b":
                        aba_c10 = 1
                        aba_answer_c.append(aba_c10)
                if no_197:
                    if no_197.suggested_answer_id.code == "b":
                        aba_c11 = 1
                        aba_answer_c.append(aba_c11)
                if no_198:
                    if no_198.suggested_answer_id.code == "b":
                        aba_c12 = 1
                        aba_answer_c.append(aba_c12)
                if no_199:
                    if no_199.suggested_answer_id.code == "b":
                        aba_c13 = 1
                        aba_answer_c.append(aba_c13)
                if no_200:
                    if no_200.suggested_answer_id.code == "b":
                        aba_c14 = 1
                        aba_answer_c.append(aba_c14)
                aba_c = len(aba_answer_c)
                
                aba_rs = aba_r + aba_c
                
                
                aba_category = ""
                if scoring_matrix:
                        line_data_aba = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == aba_rs)
                        percentile_aba = line_data_aba.abasement
                        aba_category = self.epps_personality_category(percentile_aba)
                        epps_personality_aba =  self.env['survey.epps_personality'].search([('sequence','=',10)])
                        personality_ids.append((0,0,{
                                                    'factor':"aba",
                                                    'r1':aba_r1,
                                                        'r2':aba_r2,
                                                        'r3':aba_r3,
                                                        'r4':aba_r4,
                                                        'r5':aba_r5,
                                                        'r6':aba_r6,
                                                        'r7':aba_r7,
                                                        'r8':aba_r8,
                                                        'r9':aba_r9,
                                                        'r10':aba_r10,
                                                        'r11':aba_r11,
                                                        'r12':aba_r12,
                                                        'r13':aba_r13,
                                                        'r14':aba_r14,
                                                        'r':aba_r,
                                                        'c1':aba_c1,
                                                        'c2':aba_c2,
                                                        'c3':aba_c3,
                                                        'c4':aba_c4,
                                                        'c5':aba_c5,
                                                        'c6':aba_c6,
                                                        'c7':aba_c7,
                                                        'c8':aba_c8,
                                                        'c9':aba_c9,
                                                        'c10':aba_c10,
                                                        'c11':aba_c11,
                                                        'c12':aba_c12,
                                                        'c13':aba_c13,
                                                        'c14':aba_c14,
                                                        'c':aba_c,
                                                        'rs':aba_rs,
                                                        'percentile':percentile_aba,
                                                        'category':aba_category,
                                                        'description':epps_personality_aba.description if epps_personality_aba else False
                                                    
                                                        }))
                
                
                
                
                nur_answer_r = []
                nur_answer_c = []
                nur_r1 = 0
                nur_r2 = 0
                nur_r3 = 0
                nur_r4 = 0
                nur_r5 = 0
                nur_r6 = 0
                nur_r7 = 0
                nur_r8 = 0
                nur_r9 = 0
                nur_r10 = 0
                nur_r11 = 0
                nur_r12 = 0
                nur_r13 = 0
                nur_r14 = 0
                nur_r = 0
                
                nur_c1 = 0
                nur_c2 = 0
                nur_c3 = 0
                nur_c4 = 0
                nur_c5 = 0
                nur_c6 = 0
                nur_c7 = 0
                nur_c8 = 0
                nur_c9 = 0
                nur_c10 = 0
                nur_c11 = 0
                nur_c12 = 0
                nur_c13 = 0
                nur_c14 = 0
                nur_c = 0
                
                
                if no_151:
                    if no_151.suggested_answer_id.code == "a":
                        nur_r1 = 1
                        nur_answer_r.append(nur_r1)
                if no_156:
                    if no_156.suggested_answer_id.code == "a":
                        nur_r2 = 1
                        nur_answer_r.append(nur_r2)
                if no_161:
                    if no_161.suggested_answer_id.code == "a":
                        nur_r3 = 1
                        nur_answer_r.append(nur_r3)
                if no_166:
                    if no_166.suggested_answer_id.code == "a":
                        nur_r4 = 1
                        nur_answer_r.append(nur_r4)
                if no_171:
                    if no_171.suggested_answer_id.code == "a":
                        nur_r5 = 1
                        nur_answer_r.append(nur_r5)
                if no_176:
                    if no_176.suggested_answer_id.code == "a":
                        nur_r6 = 1
                        nur_answer_r.append(nur_r6)
                if no_181:
                    if no_181.suggested_answer_id.code == "a":
                        nur_r7 = 1
                        nur_answer_r.append(nur_r7)
                if no_186:
                    if no_186.suggested_answer_id.code == "a":
                        nur_r8 = 1
                        nur_answer_r.append(nur_r8)
                if no_191:
                    if no_191.suggested_answer_id.code == "a":
                        nur_r9 = 1
                        nur_answer_r.append(nur_r9)
                if no_196:
                    if no_196.suggested_answer_id.code == "a":
                        nur_r10 = 1
                        nur_answer_r.append(nur_r10)
                if no_206:
                    if no_206.suggested_answer_id.code == "a":
                        nur_r11 = 1
                        nur_answer_r.append(nur_r11)
                if no_211:
                    if no_211.suggested_answer_id.code == "a":
                        nur_r12 = 1
                        nur_answer_r.append(nur_r12)
                if no_216:
                    if no_216.suggested_answer_id.code == "a":
                        nur_r13 = 1
                        nur_answer_r.append(nur_r13)
                if no_221:
                    if no_221.suggested_answer_id.code == "a":
                        nur_r14 = 1
                        nur_answer_r.append(nur_r14)
                
                
                nur_r = len(nur_answer_r)
                
                if no_51:
                    if no_51.suggested_answer_id.code == "b":
                        nur_c1 = 1
                        nur_answer_c.append(nur_c1)
                if no_52:
                    if no_52.suggested_answer_id.code == "b":
                        nur_c2 = 1
                        nur_answer_c.append(nur_c2)
                if no_53:
                    if no_53.suggested_answer_id.code == "b":
                        nur_c3 = 1
                        nur_answer_c.append(nur_c3)
                if no_54:
                    if no_54.suggested_answer_id.code == "b":
                        nur_c4 = 1
                        nur_answer_c.append(nur_c4)
                if no_55:
                    if no_55.suggested_answer_id.code == "b":
                        nur_c5 = 1
                        nur_answer_c.append(aba_c5)
                if no_126:
                    if no_126.suggested_answer_id.code == "b":
                        nur_c6 = 1
                        nur_answer_c.append(nur_c6)
                if no_127:
                    if no_127.suggested_answer_id.code == "b":
                        nur_c7 = 1
                        nur_answer_c.append(nur_c7)
                if no_128:
                    if no_128.suggested_answer_id.code == "b":
                        nur_c8 = 1
                        nur_answer_c.append(nur_c8)
                if no_129:
                    if no_129.suggested_answer_id.code == "b":
                        nur_c9 = 1
                        nur_answer_c.append(nur_c9)
                if no_130:
                    if no_130.suggested_answer_id.code == "b":
                        nur_c10 = 1
                        nur_answer_c.append(nur_c10)
                if no_202:
                    if no_202.suggested_answer_id.code == "b":
                        nur_c11 = 1
                        nur_answer_c.append(nur_c11)
                if no_203:
                    if no_203.suggested_answer_id.code == "b":
                        nur_c12 = 1
                        nur_answer_c.append(nur_c12)
                if no_204:
                    if no_204.suggested_answer_id.code == "b":
                        nur_c13 = 1
                        nur_answer_c.append(nur_c13)
                if no_205:
                    if no_205.suggested_answer_id.code == "b":
                        nur_c14 = 1
                        nur_answer_c.append(nur_c14)
                nur_c = len(nur_answer_c)
                
                nur_rs = nur_r + nur_c
                
                
                nur_category = ""
                if scoring_matrix:
                        line_data_nur = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == nur_rs)
                        percentile_nur = line_data_nur.nurturance
                        nur_category = self.epps_personality_category(percentile_nur)
                        epps_personality_nur =  self.env['survey.epps_personality'].search([('sequence','=',11)])
                        personality_ids.append((0,0,{
                                                    'factor':"nur",
                                                    'r1':nur_r1,
                                                        'r2':nur_r2,
                                                        'r3':nur_r3,
                                                        'r4':nur_r4,
                                                        'r5':nur_r5,
                                                        'r6':nur_r6,
                                                        'r7':nur_r7,
                                                        'r8':nur_r8,
                                                        'r9':nur_r9,
                                                        'r10':nur_r10,
                                                        'r11':nur_r11,
                                                        'r12':nur_r12,
                                                        'r13':nur_r13,
                                                        'r14':nur_r14,
                                                        'r':nur_r,
                                                        'c1':nur_c1,
                                                        'c2':nur_c2,
                                                        'c3':nur_c3,
                                                        'c4':nur_c4,
                                                        'c5':nur_c5,
                                                        'c6':nur_c6,
                                                        'c7':nur_c7,
                                                        'c8':nur_c8,
                                                        'c9':nur_c9,
                                                        'c10':nur_c10,
                                                        'c11':nur_c11,
                                                        'c12':nur_c12,
                                                        'c13':nur_c13,
                                                        'c14':nur_c14,
                                                        'c':nur_c,
                                                        'rs':nur_rs,
                                                        'percentile':percentile_nur,
                                                        'category':nur_category,
                                                        'description':epps_personality_nur.description if epps_personality_nur else False
                                                    
                                                        }))
                
                
                
                
                chg_answer_r = []
                chg_answer_c = []
                chg_r1 = 0
                chg_r2 = 0
                chg_r3 = 0
                chg_r4 = 0
                chg_r5 = 0
                chg_r6 = 0
                chg_r7 = 0
                chg_r8 = 0
                chg_r9 = 0
                chg_r10 = 0
                chg_r11 = 0
                chg_r12 = 0
                chg_r13 = 0
                chg_r14 = 0
                chg_r = 0
                
                chg_c1 = 0
                chg_c2 = 0
                chg_c3 = 0
                chg_c4 = 0
                chg_c5 = 0
                chg_c6 = 0
                chg_c7 = 0
                chg_c8 = 0
                chg_c9 = 0
                chg_c10 = 0
                chg_c11 = 0
                chg_c12 = 0
                chg_c13 = 0
                chg_c14 = 0
                chg_c = 0
                
                
                if no_152:
                    if no_152.suggested_answer_id.code == "a":
                        chg_r1 = 1
                        chg_answer_r.append(chg_r1)
                if no_157:
                    if no_157.suggested_answer_id.code == "a":
                        chg_r2 = 1
                        chg_answer_r.append(chg_r2)
                if no_162:
                    if no_162.suggested_answer_id.code == "a":
                        chg_r3 = 1
                        chg_answer_r.append(chg_r3)
                if no_167:
                    if no_167.suggested_answer_id.code == "a":
                        chg_r4 = 1
                        chg_answer_r.append(chg_r4)
                if no_172:
                    if no_172.suggested_answer_id.code == "a":
                        chg_r5 = 1
                        chg_answer_r.append(chg_r5)
                if no_177:
                    if no_177.suggested_answer_id.code == "a":
                        chg_r6 = 1
                        chg_answer_r.append(chg_r6)
                if no_182:
                    if no_182.suggested_answer_id.code == "a":
                        chg_r7 = 1
                        chg_answer_r.append(chg_r7)
                if no_187:
                    if no_187.suggested_answer_id.code == "a":
                        chg_r8 = 1
                        chg_answer_r.append(chg_r8)
                if no_192:
                    if no_192.suggested_answer_id.code == "a":
                        chg_r9 = 1
                        chg_answer_r.append(chg_r9)
                if no_197:
                    if no_197.suggested_answer_id.code == "a":
                        chg_r10 = 1
                        chg_answer_r.append(chg_r10)
                if no_202:
                    if no_202.suggested_answer_id.code == "a":
                        chg_r11 = 1
                        chg_answer_r.append(chg_r11)
                if no_212:
                    if no_212.suggested_answer_id.code == "a":
                        chg_r12 = 1
                        chg_answer_r.append(chg_r12)
                if no_217:
                    if no_217.suggested_answer_id.code == "a":
                        chg_r13 = 1
                        chg_answer_r.append(chg_r13)
                if no_222:
                    if no_222.suggested_answer_id.code == "a":
                        chg_r14 = 1
                        chg_answer_r.append(chg_r14)
                
                
                chg_r = len(chg_answer_r)
                
                if no_56:
                    if no_56.suggested_answer_id.code == "b":
                        chg_c1 = 1
                        chg_answer_c.append(chg_c1)
                if no_57:
                    if no_57.suggested_answer_id.code == "b":
                        chg_c2 = 1
                        chg_answer_c.append(chg_c2)
                if no_58:
                    if no_58.suggested_answer_id.code == "b":
                        chg_c3 = 1
                        chg_answer_c.append(chg_c3)
                if no_59:
                    if no_59.suggested_answer_id.code == "b":
                        chg_c4 = 1
                        chg_answer_c.append(chg_c4)
                if no_60:
                    if no_60.suggested_answer_id.code == "b":
                        chg_c5 = 1
                        chg_answer_c.append(chg_c5)
                if no_131:
                    if no_131.suggested_answer_id.code == "b":
                        chg_c6 = 1
                        chg_answer_c.append(chg_c6)
                if no_132:
                    if no_132.suggested_answer_id.code == "b":
                        chg_c7 = 1
                        chg_answer_c.append(chg_c7)
                if no_133:
                    if no_133.suggested_answer_id.code == "b":
                        chg_c8 = 1
                        chg_answer_c.append(chg_c8)
                if no_134:
                    if no_134.suggested_answer_id.code == "b":
                        chg_c9 = 1
                        chg_answer_c.append(chg_c9)
                if no_135:
                    if no_135.suggested_answer_id.code == "b":
                        chg_c10 = 1
                        chg_answer_c.append(chg_c10)
                if no_206:
                    if no_206.suggested_answer_id.code == "b":
                        chg_c11 = 1
                        chg_answer_c.append(chg_c11)
                if no_208:
                    if no_208.suggested_answer_id.code == "b":
                        chg_c12 = 1
                        chg_answer_c.append(chg_c12)
                if no_209:
                    if no_209.suggested_answer_id.code == "b":
                        chg_c13 = 1
                        chg_answer_c.append(chg_c13)
                if no_210:
                    if no_210.suggested_answer_id.code == "b":
                        chg_c14 = 1
                        chg_answer_c.append(chg_c14)
                chg_c = len(chg_answer_c)
                
                chg_rs = chg_r + chg_c
                
                
                chg_category = ""
                if scoring_matrix:
                        line_data_chg = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == chg_rs)
                        percentile_chg = line_data_chg.change
                        chg_category = self.epps_personality_category(percentile_chg)
                        epps_personality_chg =  self.env['survey.epps_personality'].search([('sequence','=',12)])
                        personality_ids.append((0,0,{
                                                    'factor':"chg",
                                                    'r1':chg_r1,
                                                        'r2':chg_r2,
                                                        'r3':chg_r3,
                                                        'r4':chg_r4,
                                                        'r5':chg_r5,
                                                        'r6':chg_r6,
                                                        'r7':chg_r7,
                                                        'r8':chg_r8,
                                                        'r9':chg_r9,
                                                        'r10':chg_r10,
                                                        'r11':chg_r11,
                                                        'r12':chg_r12,
                                                        'r13':chg_r13,
                                                        'r14':chg_r14,
                                                        'r':chg_r,
                                                        'c1':chg_c1,
                                                        'c2':chg_c2,
                                                        'c3':chg_c3,
                                                        'c4':chg_c4,
                                                        'c5':chg_c5,
                                                        'c6':chg_c6,
                                                        'c7':chg_c7,
                                                        'c8':chg_c8,
                                                        'c9':chg_c9,
                                                        'c10':chg_c10,
                                                        'c11':chg_c11,
                                                        'c12':chg_c12,
                                                        'c13':chg_c13,
                                                        'c14':chg_c14,
                                                        'c':chg_c,
                                                        'rs':chg_rs,
                                                        'percentile':percentile_chg,
                                                        'category':chg_category,
                                                        'description':epps_personality_chg.description if epps_personality_chg else False
                                                    
                                                        }))
                
                
                
                end_answer_r = []
                end_answer_c = []
                end_r1 = 0
                end_r2 = 0
                end_r3 = 0
                end_r4 = 0
                end_r5 = 0
                end_r6 = 0
                end_r7 = 0
                end_r8 = 0
                end_r9 = 0
                end_r10 = 0
                end_r11 = 0
                end_r12 = 0
                end_r13 = 0
                end_r14 = 0
                end_r = 0
                
                end_c1 = 0
                end_c2 = 0
                end_c3 = 0
                end_c4 = 0
                end_c5 = 0
                end_c6 = 0
                end_c7 = 0
                end_c8 = 0
                end_c9 = 0
                end_c10 = 0
                end_c11 = 0
                end_c12 = 0
                end_c13 = 0
                end_c14 = 0
                end_c = 0
                
                
                if no_153:
                    if no_153.suggested_answer_id.code == "a":
                        end_r1 = 1
                        end_answer_r.append(end_r1)
                if no_158:
                    if no_158.suggested_answer_id.code == "a":
                        end_r2 = 1
                        end_answer_r.append(end_r2)
                if no_163:
                    if no_163.suggested_answer_id.code == "a":
                        end_r3 = 1
                        end_answer_r.append(end_r3)
                if no_168:
                    if no_168.suggested_answer_id.code == "a":
                        end_r4 = 1
                        end_answer_r.append(end_r4)
                if no_173:
                    if no_173.suggested_answer_id.code == "a":
                        end_r5 = 1
                        end_answer_r.append(end_r5)
                if no_178:
                    if no_178.suggested_answer_id.code == "a":
                        end_r6 = 1
                        end_answer_r.append(end_r6)
                if no_183:
                    if no_183.suggested_answer_id.code == "a":
                        end_r7 = 1
                        end_answer_r.append(end_r7)
                if no_188:
                    if no_188.suggested_answer_id.code == "a":
                        end_r8 = 1
                        end_answer_r.append(end_r8)
                if no_193:
                    if no_193.suggested_answer_id.code == "a":
                        end_r9 = 1
                        end_answer_r.append(end_r9)
                if no_198:
                    if no_198.suggested_answer_id.code == "a":
                        end_r10 = 1
                        end_answer_r.append(end_r10)
                if no_203:
                    if no_203.suggested_answer_id.code == "a":
                        end_r11 = 1
                        end_answer_r.append(end_r11)
                if no_208:
                    if no_208.suggested_answer_id.code == "a":
                        end_r12 = 1
                        end_answer_r.append(end_r12)
                if no_218:
                    if no_218.suggested_answer_id.code == "a":
                        end_r13 = 1
                        end_answer_r.append(end_r13)
                if no_223:
                    if no_223.suggested_answer_id.code == "a":
                        end_r14 = 1
                        end_answer_r.append(end_r14)
                
                
                end_r = len(end_answer_r)
                
                if no_61:
                    if no_61.suggested_answer_id.code == "b":
                        end_c1 = 1
                        end_answer_c.append(end_c1)
                if no_62:
                    if no_62.suggested_answer_id.code == "b":
                        end_c2 = 1
                        end_answer_c.append(end_c2)
                if no_63:
                    if no_63.suggested_answer_id.code == "b":
                        end_c3 = 1
                        end_answer_c.append(end_c3)
                if no_64:
                    if no_64.suggested_answer_id.code == "b":
                        end_c4 = 1
                        end_answer_c.append(end_c4)
                if no_65:
                    if no_65.suggested_answer_id.code == "b":
                        end_c5 = 1
                        end_answer_c.append(end_c5)
                if no_136:
                    if no_136.suggested_answer_id.code == "b":
                        end_c6 = 1
                        end_answer_c.append(end_c6)
                if no_137:
                    if no_137.suggested_answer_id.code == "b":
                        end_c7 = 1
                        end_answer_c.append(end_c7)
                if no_138:
                    if no_138.suggested_answer_id.code == "b":
                        end_c8 = 1
                        end_answer_c.append(end_c8)
                if no_139:
                    if no_139.suggested_answer_id.code == "b":
                        end_c9 = 1
                        end_answer_c.append(end_c9)
                if no_140:
                    if no_140.suggested_answer_id.code == "b":
                        end_c10 = 1
                        end_answer_c.append(end_c10)
                if no_211:
                    if no_211.suggested_answer_id.code == "b":
                        end_c11 = 1
                        end_answer_c.append(end_c11)
                if no_212:
                    if no_212.suggested_answer_id.code == "b":
                        end_c12 = 1
                        end_answer_c.append(end_c12)
                if no_214:
                    if no_214.suggested_answer_id.code == "b":
                        end_c13 = 1
                        end_answer_c.append(end_c13)
                if no_215:
                    if no_215.suggested_answer_id.code == "b":
                        end_c14 = 1
                        end_answer_c.append(end_c14)
                end_c = len(end_answer_c)
                
                end_rs = end_r + end_c
                
                
                end_category = ""
                if scoring_matrix:
                        line_data_end = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == end_rs)
                        percentile_end = line_data_end.endurance
                        end_category = self.epps_personality_category(percentile_end)
                        epps_personality_end =  self.env['survey.epps_personality'].search([('sequence','=',13)])
                        personality_ids.append((0,0,{
                                                    'factor':"end",
                                                    'r1':end_r1,
                                                        'r2':end_r2,
                                                        'r3':end_r3,
                                                        'r4':end_r4,
                                                        'r5':end_r5,
                                                        'r6':end_r6,
                                                        'r7':end_r7,
                                                        'r8':end_r8,
                                                        'r9':end_r9,
                                                        'r10':end_r10,
                                                        'r11':end_r11,
                                                        'r12':end_r12,
                                                        'r13':end_r13,
                                                        'r14':end_r14,
                                                        'r':end_r,
                                                        'c1':end_c1,
                                                        'c2':end_c2,
                                                        'c3':end_c3,
                                                        'c4':end_c4,
                                                        'c5':end_c5,
                                                        'c6':end_c6,
                                                        'c7':end_c7,
                                                        'c8':end_c8,
                                                        'c9':end_c9,
                                                        'c10':end_c10,
                                                        'c11':end_c11,
                                                        'c12':end_c12,
                                                        'c13':end_c13,
                                                        'c14':end_c14,
                                                        'c':end_c,
                                                        'rs':end_rs,
                                                        'percentile':percentile_end,
                                                        'category':end_category,
                                                        'description':epps_personality_end.description if epps_personality_end else False
                                                    
                                                        }))
                
                
                
                
                het_answer_r = []
                het_answer_c = []
                het_r1 = 0
                het_r2 = 0
                het_r3 = 0
                het_r4 = 0
                het_r5 = 0
                het_r6 = 0
                het_r7 = 0
                het_r8 = 0
                het_r9 = 0
                het_r10 = 0
                het_r11 = 0
                het_r12 = 0
                het_r13 = 0
                het_r14 = 0
                het_r = 0
                
                het_c1 = 0
                het_c2 = 0
                het_c3 = 0
                het_c4 = 0
                het_c5 = 0
                het_c6 = 0
                het_c7 = 0
                het_c8 = 0
                het_c9 = 0
                het_c10 = 0
                het_c11 = 0
                het_c12 = 0
                het_c13 = 0
                het_c14 = 0
                het_c = 0
                
                
                if no_154:
                    if no_154.suggested_answer_id.code == "a":
                        het_r1 = 1
                        het_answer_r.append(het_r1)
                if no_159:
                    if no_159.suggested_answer_id.code == "a":
                        het_r2 = 1
                        het_answer_r.append(het_r2)
                if no_164:
                    if no_164.suggested_answer_id.code == "a":
                        het_r3 = 1
                        het_answer_r.append(het_r3)
                if no_169:
                    if no_169.suggested_answer_id.code == "a":
                        het_r4 = 1
                        het_answer_r.append(het_r4)
                if no_174:
                    if no_174.suggested_answer_id.code == "a":
                        het_r5 = 1
                        het_answer_r.append(het_r5)
                if no_179:
                    if no_179.suggested_answer_id.code == "a":
                        het_r6 = 1
                        het_answer_r.append(het_r6)
                if no_184:
                    if no_184.suggested_answer_id.code == "a":
                        het_r7 = 1
                        het_answer_r.append(het_r7)
                if no_189:
                    if no_189.suggested_answer_id.code == "a":
                        het_r8 = 1
                        het_answer_r.append(end_r8)
                if no_194:
                    if no_194.suggested_answer_id.code == "a":
                        het_r9 = 1
                        het_answer_r.append(het_r9)
                if no_199:
                    if no_199.suggested_answer_id.code == "a":
                        het_r10 = 1
                        het_answer_r.append(het_r10)
                if no_204:
                    if no_204.suggested_answer_id.code == "a":
                        het_r11 = 1
                        het_answer_r.append(het_r11)
                if no_209:
                    if no_209.suggested_answer_id.code == "a":
                        het_r12 = 1
                        het_answer_r.append(het_r12)
                if no_214:
                    if no_214.suggested_answer_id.code == "a":
                        het_r13 = 1
                        het_answer_r.append(het_r13)
                if no_224:
                    if no_224.suggested_answer_id.code == "a":
                        het_r14 = 1
                        het_answer_r.append(het_r14)
                
                
                het_r = len(het_answer_r)
                
                if no_66:
                    if no_66.suggested_answer_id.code == "b":
                        het_c1 = 1
                        het_answer_c.append(het_c1)
                if no_67:
                    if no_67.suggested_answer_id.code == "b":
                        het_c2 = 1
                        het_answer_c.append(het_c2)
                if no_68:
                    if no_68.suggested_answer_id.code == "b":
                        het_c3 = 1
                        het_answer_c.append(het_c3)
                if no_69:
                    if no_69.suggested_answer_id.code == "b":
                        het_c4 = 1
                        het_answer_c.append(het_c4)
                if no_70:
                    if no_70.suggested_answer_id.code == "b":
                        het_c5 = 1
                        het_answer_c.append(het_c5)
                if no_141:
                    if no_141.suggested_answer_id.code == "b":
                        het_c6 = 1
                        het_answer_c.append(het_c6)
                if no_142:
                    if no_142.suggested_answer_id.code == "b":
                        het_c7 = 1
                        het_answer_c.append(het_c7)
                if no_143:
                    if no_143.suggested_answer_id.code == "b":
                        het_c8 = 1
                        het_answer_c.append(het_c8)
                if no_144:
                    if no_144.suggested_answer_id.code == "b":
                        het_c9 = 1
                        het_answer_c.append(het_c9)
                if no_145:
                    if no_145.suggested_answer_id.code == "b":
                        het_c10 = 1
                        het_answer_c.append(het_c10)
                if no_216:
                    if no_216.suggested_answer_id.code == "b":
                        het_c11 = 1
                        het_answer_c.append(het_c11)
                if no_217:
                    if no_217.suggested_answer_id.code == "b":
                        het_c12 = 1
                        het_answer_c.append(het_c12)
                if no_218:
                    if no_218.suggested_answer_id.code == "b":
                        het_c13 = 1
                        het_answer_c.append(het_c13)
                if no_220:
                    if no_220.suggested_answer_id.code == "b":
                        het_c14 = 1
                        het_answer_c.append(het_c14)
                het_c = len(het_answer_c)
                
                het_rs = het_r + het_c
                
                
                het_category = ""
                if scoring_matrix:
                        line_data_het = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == het_rs)
                        percentile_het = line_data_het.heterosextuality
                        het_category = self.epps_personality_category(percentile_het)
                        epps_personality_het =  self.env['survey.epps_personality'].search([('sequence','=',14)])
                        personality_ids.append((0,0,{
                                                    'factor':"het",
                                                    'r1':het_r1,
                                                        'r2':het_r2,
                                                        'r3':het_r3,
                                                        'r4':het_r4,
                                                        'r5':het_r5,
                                                        'r6':het_r6,
                                                        'r7':het_r7,
                                                        'r8':het_r8,
                                                        'r9':het_r9,
                                                        'r10':het_r10,
                                                        'r11':het_r11,
                                                        'r12':het_r12,
                                                        'r13':het_r13,
                                                        'r14':het_r14,
                                                        'r':het_r,
                                                        'c1':het_c1,
                                                        'c2':het_c2,
                                                        'c3':het_c3,
                                                        'c4':het_c4,
                                                        'c5':het_c5,
                                                        'c6':het_c6,
                                                        'c7':het_c7,
                                                        'c8':het_c8,
                                                        'c9':het_c9,
                                                        'c10':het_c10,
                                                        'c11':het_c11,
                                                        'c12':het_c12,
                                                        'c13':het_c13,
                                                        'c14':het_c14,
                                                        'c':het_c,
                                                        'rs':het_rs,
                                                        'percentile':percentile_het,
                                                        'category':het_category,
                                                        'description':epps_personality_het.description if epps_personality_het else False
                                                    
                                                        }))
                
                
                
                agg_answer_r = []
                agg_answer_c = []
                agg_r1 = 0
                agg_r2 = 0
                agg_r3 = 0
                agg_r4 = 0
                agg_r5 = 0
                agg_r6 = 0
                agg_r7 = 0
                agg_r8 = 0
                agg_r9 = 0
                agg_r10 = 0
                agg_r11 = 0
                agg_r12 = 0
                agg_r13 = 0
                agg_r14 = 0
                agg_r = 0
                
                agg_c1 = 0
                agg_c2 = 0
                agg_c3 = 0
                agg_c4 = 0
                agg_c5 = 0
                agg_c6 = 0
                agg_c7 = 0
                agg_c8 = 0
                agg_c9 = 0
                agg_c10 = 0
                agg_c11 = 0
                agg_c12 = 0
                agg_c13 = 0
                agg_c14 = 0
                agg_c = 0
                
                
                if no_155:
                    if no_155.suggested_answer_id.code == "a":
                        agg_r1 = 1
                        agg_answer_r.append(agg_r1)
                if no_160:
                    if no_160.suggested_answer_id.code == "a":
                        agg_r2 = 1
                        agg_answer_r.append(agg_r2)
                if no_165:
                    if no_165.suggested_answer_id.code == "a":
                        agg_r3 = 1
                        agg_answer_r.append(agg_r3)
                if no_170:
                    if no_170.suggested_answer_id.code == "a":
                        agg_r4 = 1
                        agg_answer_r.append(agg_r4)
                if no_175:
                    if no_175.suggested_answer_id.code == "a":
                        agg_r5 = 1
                        agg_answer_r.append(agg_r5)
                if no_180:
                    if no_180.suggested_answer_id.code == "a":
                        agg_r6 = 1
                        agg_answer_r.append(agg_r6)
                if no_185:
                    if no_185.suggested_answer_id.code == "a":
                        agg_r7 = 1
                        agg_answer_r.append(agg_r7)
                if no_190:
                    if no_190.suggested_answer_id.code == "a":
                        agg_r8 = 1
                        agg_answer_r.append(agg_r8)
                if no_195:
                    if no_195.suggested_answer_id.code == "a":
                        agg_r9 = 1
                        het_answer_r.append(agg_r9)
                if no_200:
                    if no_200.suggested_answer_id.code == "a":
                        agg_r10 = 1
                        agg_answer_r.append(agg_r10)
                if no_205:
                    if no_205.suggested_answer_id.code == "a":
                        agg_r11 = 1
                        agg_answer_r.append(agg_r11)
                if no_210:
                    if no_210.suggested_answer_id.code == "a":
                        agg_r12 = 1
                        agg_answer_r.append(agg_r12)
                if no_215:
                    if no_215.suggested_answer_id.code == "a":
                        agg_r13 = 1
                        agg_answer_r.append(agg_r13)
                if no_220:
                    if no_220.suggested_answer_id.code == "a":
                        agg_r14 = 1
                        agg_answer_r.append(agg_r14)
                
                
                agg_r = len(agg_answer_r)
                
                if no_71:
                    if no_71.suggested_answer_id.code == "b":
                        agg_c1 = 1
                        agg_answer_c.append(agg_c1)
                if no_72:
                    if no_72.suggested_answer_id.code == "b":
                        agg_c2 = 1
                        agg_answer_c.append(agg_c2)
                if no_73:
                    if no_73.suggested_answer_id.code == "b":
                        agg_c3 = 1
                        agg_answer_c.append(agg_c3)
                if no_74:
                    if no_74.suggested_answer_id.code == "b":
                        agg_c4 = 1
                        agg_answer_c.append(agg_c4)
                if no_75:
                    if no_75.suggested_answer_id.code == "b":
                        agg_c5 = 1
                        agg_answer_c.append(agg_c5)
                if no_146:
                    if no_146.suggested_answer_id.code == "b":
                        agg_c6 = 1
                        agg_answer_c.append(agg_c6)
                if no_147:
                    if no_147.suggested_answer_id.code == "b":
                        agg_c7 = 1
                        agg_answer_c.append(agg_c7)
                if no_148:
                    if no_148.suggested_answer_id.code == "b":
                        agg_c8 = 1
                        agg_answer_c.append(agg_c8)
                if no_149:
                    if no_149.suggested_answer_id.code == "b":
                        agg_c9 = 1
                        agg_answer_c.append(agg_c9)
                if no_150:
                    if no_150.suggested_answer_id.code == "b":
                        agg_c10 = 1
                        agg_answer_c.append(agg_c10)
                if no_221:
                    if no_221.suggested_answer_id.code == "b":
                        agg_c11 = 1
                        agg_answer_c.append(agg_c11)
                if no_222:
                    if no_222.suggested_answer_id.code == "b":
                        agg_c12 = 1
                        agg_answer_c.append(agg_c12)
                if no_223:
                    if no_223.suggested_answer_id.code == "b":
                        agg_c13 = 1
                        agg_answer_c.append(agg_c13)
                if no_224:
                    if no_224.suggested_answer_id.code == "b":
                        agg_c14 = 1
                        agg_answer_c.append(agg_c14)
                agg_c = len(agg_answer_c)
                
                agg_rs = agg_r + agg_c
                
                
                agg_category = ""
                if scoring_matrix:
                        line_data_agg = scoring_matrix.scoring_matrix_line_ids.filtered(lambda line:line.score == agg_rs)
                        percentile_agg = line_data_agg.aggression
                        agg_category = self.epps_personality_category(percentile_agg)
                        epps_personality_agg =  self.env['survey.epps_personality'].search([('sequence','=',15)])
                        personality_ids.append((0,0,{
                                                    'factor':"agg",
                                                    'r1':agg_r1,
                                                        'r2':agg_r2,
                                                        'r3':agg_r3,
                                                        'r4':agg_r4,
                                                        'r5':agg_r5,
                                                        'r6':agg_r6,
                                                        'r7':agg_r7,
                                                        'r8':agg_r8,
                                                        'r9':agg_r9,
                                                        'r10':agg_r10,
                                                        'r11':agg_r11,
                                                        'r12':agg_r12,
                                                        'r13':agg_r13,
                                                        'r14':agg_r14,
                                                        'r':agg_r,
                                                        'c1':agg_c1,
                                                        'c2':agg_c2,
                                                        'c3':agg_c3,
                                                        'c4':agg_c4,
                                                        'c5':agg_c5,
                                                        'c6':agg_c6,
                                                        'c7':agg_c7,
                                                        'c8':agg_c8,
                                                        'c9':agg_c9,
                                                        'c10':agg_c10,
                                                        'c11':agg_c11,
                                                        'c12':agg_c12,
                                                        'c13':agg_c13,
                                                        'c14':agg_c14,
                                                        'c':agg_c,
                                                        'rs':agg_rs,
                                                        'percentile':percentile_agg,
                                                        'category':agg_category,
                                                        'description':epps_personality_agg.description if epps_personality_agg else False
                                                    
                                                        }))
                        
                    
                record.epps_peronality_result_score_ids = personality_ids
    

    def generate_papikostick(self):
        for record in self:
            if record.user_input_line_ids:
                code = 1
                # for data_papikostick_code in record.user_input_line_ids:
                #     if data_papikostick_code.suggested_answer_id:
                #         if data_papikostick_code.suggested_answer_id.papikostick_code == 1:
                #             code = 1
                #         elif data_papikostick_code.suggested_answer_id.papikostick_code == 2:
                #             code = 2
                #         elif data_papikostick_code.suggested_answer_id.papikostick_code == 3:
                #             code = 3
                #         elif data_papikostick_code.suggested_answer_id.papikostick_code == 4:
                #             code = 4
                        
                                    
                g = 0
                l = 0
                i = 0
                t = 0
                v = 0
                s = 0
                r = 0
                d = 0
                c = 0
                e = 0
                n = 0
                a = 0
                p = 0
                x = 0
                b = 0
                o = 0
                z = 0
                k = 0
                f = 0
                w = 0
                score_len = []
                
                no_1 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "1" )
                no_2 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "2"  )
                no_3 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "3" )
                no_4 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "4" )
                no_5 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "5" )
                no_6 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "6")
                no_7 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "7")
                no_8 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "8")
                no_9 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "9")
                no_10 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "10")
                no_11 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "11")
                no_12 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "12")
                no_13 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "13")
                no_14 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "14")
                no_15 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "15")
                no_16 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "16")
                no_17 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "17")
                no_18 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "18")
                no_19 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "19")
                no_20 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "20")
                no_21 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "21")
                no_22 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "22")
                no_23 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "23")
                no_24 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "24")
                no_25 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "25")
                no_26 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "26")
                no_27 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "27")
                no_28 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "28")
                no_29 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "29")
                no_30 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "30")
                no_31 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "31")
                no_32 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "32")
                no_33 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "33")
                no_34 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "34")
                no_35 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "35")
                no_36 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "36")
                no_37 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "37")
                no_38 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "38")
                no_39 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "39")
                no_40 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "40")
                no_41 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "41")
                no_42 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "42")
                no_43 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "43")
                no_44 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "44")
                no_45 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "45")
                no_46 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "46")
                no_47 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "47")
                no_48 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "48")
                no_49 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "49")
                no_50 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "50")
                no_51 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "51" )
                no_52 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "52" )
                no_53 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "53" )
                no_54 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "54" )
                no_55 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "55" )
                no_56 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "56" )
                no_57 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "57" )
                no_58 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "58" )
                no_59 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "59" )
                no_60 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "60" )
                no_61 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "61" )
                no_62 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "62" )
                no_63 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "63" )
                no_64 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "64" )
                no_65 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "65" )
                no_66 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "66" )
                no_67 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "67" )
                no_68 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "68" )
                no_69 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "69" )
                no_70 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "70" )
                no_71 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "71" )
                no_72 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "72" )
                no_73 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "73" )
                no_74 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "74" )
                no_75 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "75" )
                no_76 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "76" )
                no_77 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "77" )
                no_78 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "78")
                no_79 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "79" )
                no_80 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "80")
                no_81 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "81")
                no_82 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "82")
                no_83 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "83")
                no_84 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "84")
                no_85 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "85")
                no_86 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "86")
                no_87 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "87")
                no_88 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "88")
                no_89 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "89")
                no_90 = record.user_input_line_ids.filtered(lambda line: line.question_id.title == "90")
                
                g_list = []
                l_list = []
                i_list = []
                t_list = []
                v_list = []
                s_list = []
                r_list = []
                d_list = []
                c_list = []
                e_list = []
                n_list = []
                a_list = []
                p_list = []
                x_list = []
                b_list = []
                o_list = []
                z_list = []
                k_list = []
                f_list = []
                w_list = []
                    
                if no_1:
                    if no_1.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                    elif no_1.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                if no_2:
                    if no_2.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                    elif no_2.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                if no_3:
                    if no_3.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                    elif no_3.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                if no_4:
                    if no_4.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                    elif no_4.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                if no_5:
                    if no_5.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                    elif no_5.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                if no_6:
                    if no_6.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                    elif no_6.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                if no_7:
                    if no_7.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                    elif no_7.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                if no_8:
                    if no_8.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                    elif no_8.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                if no_9:
                    if no_9.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                    elif no_9.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_10:
                    if no_10.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                    elif no_10.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_11:
                    if no_11.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                    elif no_11.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                if no_12:
                    if no_12.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                    elif no_12.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                if no_13:
                    if no_13.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                    elif no_13.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                if no_14:
                    if no_3.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                    elif no_14.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                if no_15:
                    if no_15.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                    elif no_15.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                if no_16:
                    if no_16.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                    elif no_16.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                if no_17:
                    if no_17.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                    elif no_17.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                if no_18:
                    if no_18.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                    elif no_18.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                if no_19:
                    if no_19.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                    elif no_19.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_20:
                    if no_20.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                    elif no_20.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                if no_21:
                    if no_21.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                    elif no_21.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                if no_22:
                    if no_22.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                    elif no_22.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                if no_23:
                    if no_23.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                    elif no_23.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                if no_24:
                    if no_24.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                    elif no_24.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                if no_25:
                    if no_25.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                    elif no_25.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                if no_26:
                    if no_26.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                    elif no_26.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                if no_27:
                    if no_27.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                    elif no_27.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                if no_28:
                    if no_28.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                    elif no_28.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                if no_29:
                    if no_29.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                    elif no_29.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_30:
                    if no_30.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                    elif no_30.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                if no_31:
                    if no_31.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                    elif no_31.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                if no_32:
                    if no_32.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                    elif no_32.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                if no_33:
                    if no_33.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                    elif no_33.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                if no_34:
                    if no_34.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                    elif no_34.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                if no_35:
                    if no_35.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                    elif no_35.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                if no_36:
                    if no_36.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                    elif no_36.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                if no_37:
                    if no_37.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                    elif no_37.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                if no_38:
                    if no_38.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                    elif no_38.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                if no_39:
                    if no_39.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                    elif no_39.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_40:
                    if no_40.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                    elif no_40.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                if no_41:
                    if no_41.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                    elif no_41.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                if no_42:
                    if no_42.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                    elif no_42.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                if no_43:
                    if no_43.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                    elif no_43.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                if no_44:
                    if no_44.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                    elif no_44.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                if no_45:
                    if no_45.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                    elif no_45.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                if no_46:
                    if no_46.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                    elif no_46.suggested_answer_id.code_papikostick == "o":
                        o = 1
                        o_list.append(o)
                if no_47:
                    if no_47.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                    elif no_47.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                if no_48:
                    if no_48.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                    elif no_48.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                if no_49:
                    if no_49.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                    elif no_49.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                if no_50:
                    if no_50.suggested_answer_id.code_papikostick == "b":
                        b = 1
                        b_list.append(b)
                    elif no_50.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                if no_51:
                    if no_51.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                    elif no_51.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                if no_52:
                    if no_52.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                    elif no_52.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                if no_53:
                    if no_53.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                    elif no_53.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                if no_54:
                    if no_54.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                    elif no_54.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                if no_55:
                    if no_55.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                    elif no_55.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                if no_56:
                    if no_56.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                    elif no_56.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                if no_57:
                    if no_57.suggested_answer_id.code_papikostick == "z":
                        z = 1
                        z_list.append(z)
                    elif no_57.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                if no_58:
                    if no_58.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                    elif no_58.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                if no_59:
                    if no_59.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                    elif no_59.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                if no_60:
                    if no_60.suggested_answer_id.code_papikostick == "x":
                        x = 1
                        x_list.append(x)
                    elif no_60.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                if no_61:
                    if no_61.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                    elif no_61.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                if no_62:
                    if no_62.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                    elif no_62.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                if no_63:
                    if no_63.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                    elif no_63.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                if no_64:
                    if no_64.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                    elif no_64.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                if no_65:
                    if no_65.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                    elif no_65.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                if no_66:
                    if no_66.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                    elif no_66.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                if no_67:
                    if no_67.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                    elif no_67.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                if no_68:
                    if no_68.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                    elif no_68.suggested_answer_id.code_papikostick == "k":
                        k = 1
                        k_list.append(k)
                if no_69:
                    if no_69.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                    elif no_69.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_70:
                    if no_70.suggested_answer_id.code_papikostick == "p":
                        p = 1
                        p_list.append(p)
                    elif no_70.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                if no_71:
                    if no_71.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                    elif no_71.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                if no_72:
                    if no_72.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                    elif no_72.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                if no_73:
                    if no_73.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                    elif no_73.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                if no_74:
                    if no_74.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                    elif no_74.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                if no_75:
                    if no_75.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                    elif no_75.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                if no_76:
                    if no_76.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                    elif no_76.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                if no_77:
                    if no_77.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                    elif no_77.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                if no_78:
                    if no_78.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                    elif no_78.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                if no_79:
                    if no_79.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                    elif no_79.suggested_answer_id.code_papikostick == "f":
                        f = 1
                        f_list.append(f)
                if no_80:
                    if no_80.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                    elif no_80.suggested_answer_id.code_papikostick == "a":
                        a = 1
                        a_list.append(a)
                if no_81:
                    if no_81.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                    elif no_81.suggested_answer_id.code_papikostick == "g":
                        g = 1
                        g_list.append(g)
                if no_82:
                    if no_82.suggested_answer_id.code_papikostick == "l":
                        l = 1
                        l_list.append(l)
                    elif no_82.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                if no_83:
                    if no_83.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                    elif no_83.suggested_answer_id.code_papikostick == "i":
                        i = 1
                        i_list.append(i)
                if no_84:
                    if no_84.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                    elif no_84.suggested_answer_id.code_papikostick == "t":
                        t = 1
                        t_list.append(t)
                if no_85:
                    if no_85.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                    elif no_85.suggested_answer_id.code_papikostick == "v":
                        v = 1
                        v_list.append(v)
                if no_86:
                    if no_86.suggested_answer_id.code_papikostick == "s":
                        s = 1
                        s_list.append(s)
                    elif no_86.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                if no_87:
                    if no_87.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                    elif no_87.suggested_answer_id.code_papikostick == "r":
                        r = 1
                        r_list.append(r)
                if no_88:
                    if no_88.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                    elif no_88.suggested_answer_id.code_papikostick == "d":
                        d = 1
                        d_list.append(d)
                if no_89:
                    if no_89.suggested_answer_id.code_papikostick == "c":
                        c = 1
                        c_list.append(c)
                    elif no_89.suggested_answer_id.code_papikostick == "e":
                        e = 1
                        e_list.append(e)
                if no_90:
                    if no_90.suggested_answer_id.code_papikostick == "n":
                        n = 1
                        n_list.append(n)
                    elif no_90.suggested_answer_id.code_papikostick == "w":
                        w = 1
                        w_list.append(w)
                
                total_g = len(g_list)
                total_l = len(l_list)
                total_i = len(i_list)
                total_t = len(t_list)
                total_v = len(v_list)
                total_s = len(s_list)
                total_r = len(r_list)
                total_d = len(d_list)
                total_c = len(c_list)
                total_e = len(e_list)
                total_n = len(n_list)
                total_a = len(a_list)
                total_p = len(p_list)
                total_x = len(x_list)
                total_b = len(b_list)
                total_o = len(o_list)
                total_z = len(z_list)
                total_k = len(k_list)
                total_f = len(f_list)
                total_w = len(w_list)

                total_score = total_g + total_l+ total_i + total_t + total_v + total_s + total_r + total_d + total_c + total_e + total_n + total_a + total_p + total_x + total_b + total_o + total_z + total_k + total_f + total_w                    

                avg_work_direction = (total_n + total_g + total_a) / 3
                avg_leadership = (total_l + total_p + total_i) / 3
                avg_activity = (total_t + total_v) / 2
                avg_social_nature = (total_x + total_s + total_b + total_o) / 4
                avg_work_style = (total_r + total_d + total_c) / 3
                avg_temperament = (total_z + total_e + total_k) / 3
                avg_follower = (total_f + total_w) / 2

                # percentile = 0
                # category = ""
                parameter_list = []
                parameter_line = {}
                papikostick_param = self.env['papikostick.parameter.root'].search([])
                for param in papikostick_param:
                    parameter_list.append(param.parameter)
                
                for param_line in papikostick_param.parameter_ids:
                    parameter_line[param_line.code] = param_line.parameter_line
                
                print("///////// param line: ", parameter_line)
                # if papikostick_param:
                #     line_data = papikostick_param.parameter_ids.filtered(lambda line:line.score == len(score_len))
                #     percentile = line_data.consistency
                #     category = self.epps_category(percentile)
                    
                record.papikostick_result_ids = [(0,0,{
                                                'g_field': total_g,
                                                'l_field': total_l,
                                                'i_field': total_i,
                                                't_field': total_t,
                                                'v_field': total_v,
                                                's_field': total_s,
                                                'r_field': total_r,
                                                'd_field': total_d,
                                                'c_field': total_c,
                                                'e_field': total_e,
                                                'n_field': total_n,
                                                'a_field': total_a,
                                                'p_field': total_p,
                                                'x_field': total_x,
                                                'b_field': total_b,
                                                'o_field': total_o,
                                                'z_field': total_z,
                                                'k_field': total_k,
                                                'f_field': total_f,
                                                'w_field': total_w,
                                                'total_field': total_score                                                
                                                })]

                parameter_score_list = [
                    avg_work_direction,
                    avg_leadership,
                    avg_activity,
                    avg_social_nature,
                    avg_work_style,
                    avg_temperament,
                    avg_follower
                ]

                parameter_line_list_1 = []
                parameter_line_list_2 = []
                parameter_line_list_3 = []
                parameter_line_list_4 = []
                parameter_line_list_5 = []
                parameter_line_list_6 = []
                parameter_line_list_7 = []
                
                code_pl_list_1 = []
                code_pl_list_2 = []
                code_pl_list_3 = []
                code_pl_list_4 = []
                code_pl_list_5 = []
                code_pl_list_6 = []
                code_pl_list_7 = []

                analysis_score_1 = []
                analysis_score_2 = []
                analysis_score_3 = []
                analysis_score_4 = []
                analysis_score_5 = []
                analysis_score_6 = []
                analysis_score_7 = []

                score_code_1 = []
                score_code_2 = []
                score_code_3 = []
                score_code_4 = []
                score_code_5 = []
                score_code_6 = []
                score_code_7 = []

                if total_n <= 3:
                    analysis_score_1.append("LOW ANALYSIS")
                elif total_n <= 6:
                    analysis_score_1.append("MIDDLE RANGE")
                else:
                    analysis_score_1.append("HIGH ANALYSIS")

                if total_g <= 3:
                    analysis_score_1.append("LOW ANALYSIS")
                elif total_g <= 6:
                    analysis_score_1.append("MIDDLE RANGE")
                else:
                    analysis_score_1.append("HIGH ANALYSIS")
                
                if total_a <= 3:
                    analysis_score_1.append("LOW ANALYSIS")
                elif total_a <= 6:
                    analysis_score_1.append("MIDDLE RANGE")
                else:
                    analysis_score_1.append("HIGH ANALYSIS")
                
                if total_l <= 3:
                    analysis_score_2.append("LOW ANALYSIS")
                elif total_l <= 6:
                    analysis_score_2.append("MIDDLE RANGE")
                else:
                    analysis_score_2.append("HIGH ANALYSIS")
                
                if total_p <= 3:
                    analysis_score_2.append("LOW ANALYSIS")
                elif total_p <= 6:
                    analysis_score_2.append("MIDDLE RANGE")
                else:
                    analysis_score_2.append("HIGH ANALYSIS")
                
                if total_i <= 3:
                    analysis_score_2.append("LOW ANALYSIS")
                elif total_i <= 6:
                    analysis_score_2.append("MIDDLE RANGE")
                else:
                    analysis_score_2.append("HIGH ANALYSIS")
                
                if total_t <= 3:
                    analysis_score_3.append("LOW ANALYSIS")
                elif total_t <= 6:
                    analysis_score_3.append("MIDDLE RANGE")
                else:
                    analysis_score_3.append("HIGH ANALYSIS")
                
                if total_v <= 3:
                    analysis_score_3.append("LOW ANALYSIS")
                elif total_v <= 6:
                    analysis_score_3.append("MIDDLE RANGE")
                else:
                    analysis_score_3.append("HIGH ANALYSIS")
                
                if total_x <= 3:
                    analysis_score_4.append("LOW ANALYSIS")
                elif total_x <= 6:
                    analysis_score_4.append("MIDDLE RANGE")
                else:
                    analysis_score_4.append("HIGH ANALYSIS")
                
                if total_s <= 3:
                    analysis_score_4.append("LOW ANALYSIS")
                elif total_s <= 6:
                    analysis_score_4.append("MIDDLE RANGE")
                else:
                    analysis_score_4.append("HIGH ANALYSIS")
                
                if total_b <= 3:
                    analysis_score_4.append("LOW ANALYSIS")
                elif total_b <= 6:
                    analysis_score_4.append("MIDDLE RANGE")
                else:
                    analysis_score_4.append("HIGH ANALYSIS")
                
                if total_o <= 3:
                    analysis_score_4.append("LOW ANALYSIS")
                elif total_o <= 6:
                    analysis_score_4.append("MIDDLE RANGE")
                else:
                    analysis_score_4.append("HIGH ANALYSIS")
                
                if total_r <= 3:
                    analysis_score_5.append("LOW ANALYSIS")
                elif total_r <= 6:
                    analysis_score_5.append("MIDDLE RANGE")
                else:
                    analysis_score_5.append("HIGH ANALYSIS")
                
                if total_d <= 3:
                    analysis_score_5.append("LOW ANALYSIS")
                elif total_d <= 6:
                    analysis_score_5.append("MIDDLE RANGE")
                else:
                    analysis_score_5.append("HIGH ANALYSIS")
                
                if total_c <= 3:
                    analysis_score_5.append("LOW ANALYSIS")
                elif total_c <= 6:
                    analysis_score_5.append("MIDDLE RANGE")
                else:
                    analysis_score_5.append("HIGH ANALYSIS")
                
                if total_z <= 3:
                    analysis_score_6.append("LOW ANALYSIS")
                elif total_z <= 6:
                    analysis_score_6.append("MIDDLE RANGE")
                else:
                    analysis_score_6.append("HIGH ANALYSIS")
                
                if total_e <= 3:
                    analysis_score_6.append("LOW ANALYSIS")
                elif total_e <= 6:
                    analysis_score_6.append("MIDDLE RANGE")
                else:
                    analysis_score_6.append("HIGH ANALYSIS")
                
                if total_k <= 3:
                    analysis_score_6.append("LOW ANALYSIS")
                elif total_k <= 6:
                    analysis_score_6.append("MIDDLE RANGE")
                else:
                    analysis_score_6.append("HIGH ANALYSIS")
                
                if total_f <= 3:
                    analysis_score_7.append("LOW ANALYSIS")
                elif total_f <= 6:
                    analysis_score_7.append("MIDDLE RANGE")
                else:
                    analysis_score_7.append("HIGH ANALYSIS")
                
                if total_w <= 3:
                    analysis_score_7.append("LOW ANALYSIS")
                elif total_w <= 6:
                    analysis_score_7.append("MIDDLE RANGE")
                else:
                    analysis_score_7.append("HIGH ANALYSIS")

                for key, val in parameter_line.items():
                    if key == 'N' and val == 'Need to Personality Finish a Task':
                        parameter_line_list_1.append(val)
                        code_pl_list_1.append(key)
                        score_code_1.append(str(total_n))
                    elif key == 'G' and val == 'Role of hard intense worker':
                        parameter_line_list_1.append(val)
                        code_pl_list_1.append(key)
                        score_code_1.append(str(total_g))
                    elif key == 'A' and val == 'Need to Achieve':
                        parameter_line_list_1.append(val)
                        code_pl_list_1.append(key)
                        score_code_1.append(str(total_a))
                    elif key == 'L' and val == 'Leadership Role':
                        parameter_line_list_2.append(val)
                        code_pl_list_2.append(key)
                        score_code_2.append(str(total_l))
                    elif key == 'P' and val == 'Need to Control Others':
                        parameter_line_list_2.append(val)
                        code_pl_list_2.append(key)
                        score_code_2.append(str(total_p))
                    elif key == 'I' and val == 'Ease in Decision Making':
                        parameter_line_list_2.append(val)
                        code_pl_list_2.append(key)
                        score_code_2.append(str(total_i))
                    elif key == 'T' and val == '"On the Go" Type':
                        parameter_line_list_3.append(val)
                        code_pl_list_3.append(key)
                        score_code_3.append(str(total_t))
                    elif key == 'V' and val == 'Vigorous Type':
                        parameter_line_list_3.append(val)
                        code_pl_list_3.append(key)
                        score_code_3.append(str(total_v))
                    elif key == 'X' and val == 'Need to be Noticed':
                        parameter_line_list_4.append(val)
                        code_pl_list_4.append(key)
                        score_code_4.append(str(total_x))
                    elif key == 'S' and val == 'Social Extension':
                        parameter_line_list_4.append(val)
                        code_pl_list_4.append(key)
                        score_code_4.append(str(total_s))
                    elif key == 'B' and val == 'Need to Belong to Group':
                        parameter_line_list_4.append(val)
                        code_pl_list_4.append(key)
                        score_code_4.append(str(total_b))
                    elif key == 'O' and val == 'Need for Closeness and Affection':
                        parameter_line_list_4.append(val)
                        code_pl_list_4.append(key)
                        score_code_4.append(str(total_o))
                    elif key == 'R' and val == 'Theoritical Type':
                        parameter_line_list_5.append(val)
                        code_pl_list_5.append(key)
                        score_code_5.append(str(total_r))
                    elif key == 'D' and val == 'Interest in Working with Details':
                        parameter_line_list_5.append(val)
                        code_pl_list_5.append(key)
                        score_code_5.append(str(total_d))
                    elif key == 'C' and val == 'Organized Type':
                        parameter_line_list_5.append(val)
                        code_pl_list_5.append(key)
                        score_code_5.append(str(total_c))
                    elif key == 'Z' and val == 'Need for Change':
                        parameter_line_list_6.append(val)
                        code_pl_list_6.append(key)
                        score_code_6.append(str(total_z))
                    elif key == 'E' and val == 'Emotional Restaint':
                        parameter_line_list_6.append(val)
                        code_pl_list_6.append(key)
                        score_code_6.append(str(total_e))
                    elif key == 'K' and val == 'Need for Defensive Aggressiveness':
                        parameter_line_list_6.append(val)
                        code_pl_list_6.append(key)
                        score_code_6.append(str(total_k))
                    elif key == 'F' and val == 'Need to Support Authority':
                        parameter_line_list_7.append(val)
                        code_pl_list_7.append(key)
                        score_code_7.append(str(total_f))
                    elif key == 'W' and val == 'Need for Rule and Supervision':
                        parameter_line_list_7.append(val)
                        code_pl_list_7.append(key)
                        score_code_7.append(str(total_w))
                
                join_parameter_line_list_1 = "\n".join(parameter_line_list_1)
                join_parameter_line_list_2 = "\n".join(parameter_line_list_2)
                join_parameter_line_list_3 = "\n".join(parameter_line_list_3)
                join_parameter_line_list_4 = "\n".join(parameter_line_list_4)
                join_parameter_line_list_5 = "\n".join(parameter_line_list_5)
                join_parameter_line_list_6 = "\n".join(parameter_line_list_6)
                join_parameter_line_list_7 = "\n".join(parameter_line_list_7)
                
                join_code_pl_list_1 = "\n".join(code_pl_list_1)
                join_code_pl_list_2 = "\n".join(code_pl_list_2)
                join_code_pl_list_3 = "\n".join(code_pl_list_3)
                join_code_pl_list_4 = "\n".join(code_pl_list_4)
                join_code_pl_list_5 = "\n".join(code_pl_list_5)
                join_code_pl_list_6 = "\n".join(code_pl_list_6)
                join_code_pl_list_7 = "\n".join(code_pl_list_7)

                join_analysis_score_1 = "\n".join(analysis_score_1)
                join_analysis_score_2 = "\n".join(analysis_score_2)
                join_analysis_score_3 = "\n".join(analysis_score_3)
                join_analysis_score_4 = "\n".join(analysis_score_4)
                join_analysis_score_5 = "\n".join(analysis_score_5)
                join_analysis_score_6 = "\n".join(analysis_score_6)
                join_analysis_score_7 = "\n".join(analysis_score_7)

                join_score_code_1 = "\n".join(score_code_1)
                join_score_code_2 = "\n".join(score_code_2)
                join_score_code_3 = "\n".join(score_code_3)
                join_score_code_4 = "\n".join(score_code_4)
                join_score_code_5 = "\n".join(score_code_5)
                join_score_code_6 = "\n".join(score_code_6)
                join_score_code_7 = "\n".join(score_code_7)

                parameter_line_dict = {
                    join_code_pl_list_1: join_parameter_line_list_1,
                    join_code_pl_list_2: join_parameter_line_list_2,
                    join_code_pl_list_3: join_parameter_line_list_3,
                    join_code_pl_list_4: join_parameter_line_list_4,
                    join_code_pl_list_5: join_parameter_line_list_5,
                    join_code_pl_list_6: join_parameter_line_list_6,
                    join_code_pl_list_7: join_parameter_line_list_7,
                }

                analysis_score = [
                    join_analysis_score_1,
                    join_analysis_score_2,
                    join_analysis_score_3,
                    join_analysis_score_4,
                    join_analysis_score_5,
                    join_analysis_score_6,
                    join_analysis_score_7
                ]

                score_code = [
                    join_score_code_1,
                    join_score_code_2,
                    join_score_code_3,
                    join_score_code_4,
                    join_score_code_5,
                    join_score_code_6,
                    join_score_code_7
                ]

                parameter_line_code = list(parameter_line_dict)
                description_code = list(parameter_line_dict.values())

                for i in range(len(parameter_list)):
                    record.papikostick_parameter_result_ids = [(0,0,{
                        'parameter': parameter_list[i],
                        # 'description': description_code[i],
                        'code_pl': parameter_line_code[i],
                        'score_code': score_code[i],
                        'description_code': description_code[i],
                        'analysis': analysis_score[i],
                        'score': parameter_score_list[i]
                    })]                           
                

    def generate_mbti(self):
        for record in self:
            total_e = 0
            total_i = 0
            total_s = 0
            total_n = 0
            total_t = 0
            total_f = 0
            total_j = 0
            total_p = 0

            total_e_questions = 0
            total_i_questions = 0
            total_s_questions = 0
            total_n_questions = 0
            total_t_questions = 0
            total_f_questions = 0
            total_j_questions = 0
            total_p_questions = 0
            result = []

            mbti_questions = self.env['survey.question'].search([('question_type', '=', 'mbti')])
            for line in mbti_questions.suggested_answer_ids:
                if line.mbti_code == 'e':
                    total_e_questions += 1
                elif line.mbti_code == 'i':
                    total_i_questions += 1
                elif line.mbti_code == 's':
                    total_s_questions += 1
                elif line.mbti_code == 'n':
                    total_n_questions += 1
                elif line.mbti_code == 't':
                    total_t_questions += 1
                elif line.mbti_code == 'f':
                    total_f_questions += 1
                elif line.mbti_code == 'j':
                    total_j_questions += 1
                elif line.mbti_code == 'p':
                    total_p_questions += 1            

            if record.user_input_line_ids:
                for question in record.user_input_line_ids:
                    if question.question_id.sequence == 1:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 2:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 3:
                        if question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                        elif question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                    if question.question_id.sequence == 4:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 5:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 6:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 7:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 8:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 9:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 10:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 11:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 12:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 13:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 14:
                        if question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                        elif question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                    if question.question_id.sequence == 15:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 16:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 17:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 18:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 19:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 20:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 21:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 22:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 23:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 24:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 25:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 26:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 27:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 28:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 29:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 30:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 31:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 32:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 33:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 34:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 35:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 36:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 37:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 38:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 39:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 40:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 41:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 42:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_p += 1
                    if question.question_id.sequence == 43:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 44:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 45:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 46:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 47:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 48:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 49:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 50:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 51:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 52:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 53:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 54:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 55:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 56:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 57:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 58:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 59:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 60:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 61:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 62:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 63:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 64:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 65:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 66:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_n += 1
                    if question.question_id.sequence == 67:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 68:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 69:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 70:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1
                    if question.question_id.sequence == 71:
                        if question.suggested_answer_id.mbti_code == 'e':
                            total_e += 1
                        elif question.suggested_answer_id.mbti_code == 'i':
                            total_i += 1
                    if question.question_id.sequence == 72:
                        if question.suggested_answer_id.mbti_code == 's':
                            total_s += 1
                        elif question.suggested_answer_id.mbti_code == 'n':
                            total_s += 1
                    if question.question_id.sequence == 73:
                        if question.suggested_answer_id.mbti_code == 't':
                            total_t += 1
                        elif question.suggested_answer_id.mbti_code == 'f':
                            total_f += 1
                    if question.question_id.sequence == 74:
                        if question.suggested_answer_id.mbti_code == 'j':
                            total_j += 1
                        elif question.suggested_answer_id.mbti_code == 'p':
                            total_p += 1

                # calculate the percentage
                e_percentage = (total_e / total_e_questions) * 100
                i_percentage = (total_i / total_i_questions) * 100
                s_percentage = (total_s / total_s_questions) * 100
                n_percentage = (total_n / total_n_questions) * 100
                t_percentage = (total_t / total_t_questions) * 100
                f_percentage = (total_f / total_f_questions) * 100
                j_percentage = (total_j / total_j_questions) * 100
                p_percentage = (total_p / total_p_questions) * 100

                dimensional_scores = [i_percentage, e_percentage, s_percentage, n_percentage,
                                      t_percentage, f_percentage, j_percentage, p_percentage]
                mbti_variables = self.env['mbti.variable'].search([])
                personality_names = [variable.name for variable in mbti_variables]

                for index in range(len(personality_names)):
                    record.dimensional_score_ids = [(0,0,{
                        'name': personality_names[index],
                        'score': dimensional_scores[index],
                    })]
                    

                if e_percentage > i_percentage:
                    result.append("e")
                else:
                    result.append("i")
                if s_percentage > n_percentage:
                    result.append("s")
                else :
                    result.append("n")
                if t_percentage > f_percentage:
                    result.append("t")
                else:
                    result.append("f")
                if j_percentage > p_percentage:
                    result.append("j")
                else:
                    result.append("p")

                # Result based on paramaters
                personality_result = "".join(result).upper()
                mbti_parameters = self.env['mbti.parameter.root'].search([('name', '=', personality_result)])

                if mbti_parameters:
                    for parameter in mbti_parameters:
                        record.mbti_final_result_ids = [(0,0,{
                            'name': parameter.name,
                            'description': parameter.description,
                            'advice_and_self_development': parameter.advice_and_self_development,
                            'suitable_profession': parameter.suitable_profession,
                            'famous_figure': parameter.famous_figure,
                            'population': parameter.frequency_in_population,
                            'job_position': parameter.job_position,
                            'representation': parameter.representation
                        })]

                for variable in mbti_variables:
                    for code in result:
                        if variable.code == code:
                            record.mbti_personality_result_ids = [(0,0,{
                                'name': variable.name,
                                'code': variable.code,
                                'description': variable.description,
                            })]



                
    def get_languange(self):
        languange = self.user_input_line_ids.filtered(lambda line: line.suggested_answer_id.question_id.is_question_languange)
        if languange:
            return languange.suggested_answer_id.value    
            
    


    def _get_mask_public_self(self):
        for record in self:
            if record.mask_public_self:
                line_ids = []
                languange = record.get_languange()
                # if str(languange).lower() == 'indonesia':
                #     for data in record.mask_public_self.personality.personality_ids:
                #         line_ids.append((0,0,{'personality':data.personality}))
                # else:
                for data in record.mask_public_self.personality.personality_ids:
                    line_ids.append((0,0,{'personality':data.personality,
                                          'personality_en':data.personality_en
                                          
                                          
                                          }))
                if not record.mask_public_self_ids:
                    record.mask_public_self_ids = line_ids
                record.shadow_field_mask_public_self = True
            else:
                record.mask_public_self_ids = False
                record.shadow_field_mask_public_self = False

    def _get_mirror_perceived_self(self):
        for record in self:
            if record.mirror_perceived_self:
                line_ids = []
                # languange = record.get_languange()
                # if str(languange).lower() == 'indonesia':
                #     for data in record.mirror_perceived_self.personality.personality_ids:
                #         record.personal_description = record.mirror_perceived_self.personality_description
                #         line_ids.append((0,0,{'personality':data.personality}))
                # else:
                for data in record.mirror_perceived_self.personality.personality_ids:
                    line_ids.append((0,0,{'personality':data.personality,
                                          'personality_en':data.personality_en,
                                          
                                          
                                          }))
                record.personal_description = record.mirror_perceived_self.personality_description
                record.personal_description_en = record.mirror_perceived_self.personality_description_en
                if not record.mirror_perceived_self_ids:
                    record.mirror_perceived_self_ids = line_ids
                
                record.job_match = record.mirror_perceived_self.job_matches
                if not record.job_suggestion:
                    job_ids = []
                    for data_job in record.mirror_perceived_self.job_suggestion_ids:
                        job_list = [data.id for data in data_job.job_suggestion]
                        if job_list:
                            job_ids.extend(job_list)
                    if job_ids:
                        record.job_suggestion = [(6,0,job_ids)]
                record.shadow_field_mirror_perceived_self = True
            else:
                record.mirror_perceived_self_ids = False
                record.shadow_field_mirror_perceived_self = False

    def _get_core_private_self(self):
        for record in self:
            if record.core_private_self:
                line_ids = []
                languange = record.get_languange()
                # if str(languange).lower() == 'indonesia':
                #     for data in record.core_private_self.personality.personality_ids:
                #         line_ids.append((0,0,{'personality':data.personality}))
                # else:
                for data in record.core_private_self.personality.personality_ids:
                    line_ids.append((0,0,{'personality':data.personality,
                                          'personality_en':data.personality_en
                                          
                                          }))
                if not record.core_private_self_ids:
                    record.core_private_self_ids = line_ids
                record.shadow_field_core_private_self = True
            else:
                record.core_private_self_ids = False
                record.shadow_field_core_private_self = False





    def generate(self):
        for record in self:
            line_ids = []
            len_d_m = len([data.id for data in record.user_input_line_ids.filtered(lambda line:line.suggested_answer_id.value == 'M' and line.code == 'D' )])
            len_i_m = len([data.id for data in record.user_input_line_ids.filtered(lambda line:line.suggested_answer_id.value == 'M' and line.code == 'I' )])
            len_s_m = len([data.id for data in record.user_input_line_ids.filtered(lambda line:line.suggested_answer_id.value == 'M' and line.code == 'S' )])
            len_c_m = len([data.id for data in record.user_input_line_ids.filtered(lambda line:line.suggested_answer_id.value == 'M' and line.code == 'C' )])
            len_star_m = len([data.id for data in record.user_input_line_ids.filtered(lambda line:line.suggested_answer_id.value == 'M' and line.code == '*' )])
            total = len_d_m + len_i_m + len_s_m + len_c_m +len_star_m
            line_ids.append((0,0,{'line':1,'d_field':len_d_m,'i_field':len_i_m,'s_field':len_s_m,'c_field':len_c_m,'star_field':len_star_m,'total_field':total}))

            len_d_s = len([data.id for data in record.user_input_line_ids.filtered(lambda line: line.suggested_answer_id.value == 'L' and line.code == 'D')])
            len_i_s = len([data.id for data in record.user_input_line_ids.filtered(lambda line: line.suggested_answer_id.value == 'L' and line.code == 'I')])
            len_s_s = len([data.id for data in record.user_input_line_ids.filtered(lambda line: line.suggested_answer_id.value == 'L' and line.code == 'S')])
            len_c_s = len([data.id for data in record.user_input_line_ids.filtered(lambda line: line.suggested_answer_id.value == 'L' and line.code == 'C')])
            len_star_s = len([data.id for data in record.user_input_line_ids.filtered(lambda line: line.suggested_answer_id.value == 'L' and line.code == '*')])
            total_s = len_d_s+ len_i_s + len_s_s + len_c_s+ len_star_s
            line_ids.append((0, 0,{'line': 2, 'd_field': len_d_s, 'i_field': len_i_s, 's_field': len_s_s, 'c_field': len_c_s,'star_field': len_star_s, 'total_field': total_s}))
            line_ids.append((0, 0,{'line': 3, 'd_field': len_d_m - len_d_s, 'i_field': len_i_m - len_i_s, 's_field': len_s_m - len_s_s, 'c_field': len_c_m - len_c_s}))
            record.disc_result_ids = line_ids
            record.generate_score2()
            record.generate_score3()
            record.generate_final_score()
            record.is_hide_generate = True



    def generate_score2(self):
        for record in self:
            line_ids = []
            line_1 = record.disc_result_ids.filtered(lambda line:line.line==1)
            line_1_d_field = self.env['disc.scoring.matrix.line'].search([('score','=',line_1.d_field),('is_line_1','=',True)])
            line_1_i_field = self.env['disc.scoring.matrix.line'].search([('score','=',line_1.i_field),('is_line_1','=',True)])
            line_1_s_field = self.env['disc.scoring.matrix.line'].search([('score','=',line_1.s_field),('is_line_1','=',True)])
            line_1_c_field = self.env['disc.scoring.matrix.line'].search([('score','=',line_1.c_field),('is_line_1','=',True)])
            line_ids.append((0, 0,{'line': 1, 'd_field':line_1_d_field.d_field , 'i_field':line_1_i_field.i_field , 's_field':line_1_s_field.s_field , 'c_field': line_1_c_field.c_field}))
            line_2 = record.disc_result_ids.filtered(lambda line:line.line==2)
            line_2_d_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_2.d_field), ('is_line_2', '=', True)])
            line_2_i_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_2.i_field), ('is_line_2', '=', True)])
            line_2_s_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_2.s_field), ('is_line_2', '=', True)])
            line_2_c_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_2.c_field), ('is_line_2', '=', True)])
            line_ids.append((0, 0, {'line': 2, 'd_field': line_2_d_field.d_field, 'i_field': line_2_i_field.i_field,'s_field': line_2_s_field.s_field, 'c_field': line_2_c_field.c_field}))
            line_3 = record.disc_result_ids.filtered(lambda line: line.line == 3)
            line_3_d_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_3.d_field), ('is_line_3', '=', True)])
            line_3_i_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_3.i_field), ('is_line_3', '=', True)])
            line_3_s_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_3.s_field), ('is_line_3', '=', True)])
            line_3_c_field = self.env['disc.scoring.matrix.line'].search(
                [('score', '=', line_3.c_field), ('is_line_3', '=', True)])
            line_ids.append((0, 0, {'line': 3, 'd_field': line_3_d_field.d_field, 'i_field': line_3_i_field.i_field,'s_field': line_3_s_field.s_field, 'c_field': line_3_c_field.c_field}))
            record.disc_result_score2_ids = line_ids


    def generate_score3(self):
        for record in self:
            score_ids = []
            score_ids_2 = []
            score_ids_3 = []
            line_ids = []
            c_1 = 0
            d_1 = 0
            c_d_1 = 0
            i_d_1 = 0
            i_d_c_1 = 0
            i_d_s_1 = 0
            i_s_d_1 = 0
            s_d_c_1 = 0
            d_c_1 = 0
            d_i_1 = 0
            d_i_s_1 = 0
            d_s_1 = 0
            c_i_s_1 = 0
            c_s_i_1 = 0
            i_s_c_i_c_s_1 = 0
            s_1 = 0
            c_s_1 = 0
            s_c_1 = 0
            d_i_c_1 = 0
            d_s_i_1 = 0
            d_s_c_1 = 0
            d_c_i_1 = 0
            d_c_s_1 =0
            i_1 = 0
            i_s_1 = 0
            i_c_1 = 0
            i_c_d_1 = 0
            i_c_s_1 = 0
            s_i_1 = 0
            s_d_1 = 0
            s_d_i_1 = 0
            s_i_d_1 = 0
            s_i_c_1 = 0
            s_c_d_1 = 0
            s_c_i_1 = 0
            c_i_1 = 0
            c_d_i_1 = 0
            c_d_s_1 = 0
            c_i_d_1 = 0
            c_s_d_1 = 0
            line_1 = record.disc_result_score2_ids.filtered(lambda line:line.line==1)
            D_1 = line_1.d_field
            I_1 = line_1.i_field
            S_1 = line_1.s_field
            C_1 = line_1.c_field

            if D_1 <= 0 and I_1 <= 0 and S_1 <= 0 and C_1 > 0:
                c_1 = 1
                score_ids.append(1)
            if D_1 > 0 and I_1 <= 0 and S_1 <= 0 and C_1 <= 0:
                d_1 = 1
                score_ids.append(2)
            if D_1 > 0 and I_1 <= 0 and S_1 <= 0 and C_1 > 0 and C_1 >= D_1:
                c_d_1 = 1
                score_ids.append(3)
            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 <= 0 and I_1 >= D_1:
                i_d_1 = 1
                score_ids.append(4)
            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and I_1 >= D_1 >= C_1:
                i_d_c_1 = 1
                score_ids.append(5)
            if D_1 > 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and I_1 >= D_1 >= S_1:
                i_d_s_1 = 1
                score_ids.append(6)
            if D_1 > 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and I_1 >= S_1 >= D_1:
                i_s_d_1 = 1
                score_ids.append(7)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and S_1 >= D_1 and D_1 >= C_1:
                s_d_c_1 = 1
                score_ids.append(8)
            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 <= 0 and D_1 >= I_1:
                d_c_1 = 1
                score_ids.append(9)
            if D_1 > 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and D_1 >= I_1 >= S_1:
                d_i_1 = 1
                score_ids.append(10)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 <= 0 and D_1 >=  S_1:
                d_i_s_1 = 1
                score_ids.append(11)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 > 0 and C_1 >= I_1 >= S_1:
                d_s_1 = 1
                score_ids.append(12)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 > 0 and C_1 >=  S_1 >= I_1:
                c_i_s_1 = 1
                score_ids.append(13)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 > 0 and I_1 >=  S_1 and I_1 >= C_1:
                c_s_i_1 = 1
                score_ids.append(14)
            if D_1 <= 0 and I_1 <= 0 and S_1 > 0 and C_1 <= 0:
                i_s_c_i_c_s_1 = 1
                score_ids.append(15)
            if D_1 <= 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and C_1 >= S_1:
                s_1 = 1
                score_ids.append(16)
            if D_1 <= 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and S_1 >= C_1:
                c_s_1 = 1
                score_ids.append(17)
            if D_1 > 0 and I_1 <= 0 and S_1 <= 0 and C_1 > 0 and D_1 >= C_1:
                s_c_1 = 1
                score_ids.append(18)
            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and D_1 >= I_1 >= C_1:
                d_i_c_1 = 1
                score_ids.append(19)

            if D_1 > 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and D_1 >= S_1 >= I_1:
                d_s_i_1 = 1
                score_ids.append(20)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and D_1 >= S_1 and S_1 >= C_1:
                d_s_c_1 = 1
                score_ids.append(21)
            if D_1 > 0 and I_1 >0 and S_1 <= 0 and C_1 > 0 and D_1 >= C_1 and C_1 >= I_1:
                d_c_i_1 = 1
                score_ids.append(22)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and D_1 >= C_1 and C_1 >= S_1:
                d_c_s_1 = 1
                score_ids.append(23)
            if D_1 <= 0 and I_1 > 0 and S_1 <= 0 and C_1 <= 0:
                i_1 = 1
                score_ids.append(24)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and I_1>= S_1:
                i_s_1 = 1
                score_ids.append(25)

            if D_1 <= 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and I_1 >= C_1:
                i_c_1 = 1
                score_ids.append(26)


            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and I_1 >= C_1 and C_1>=D_1:
                i_c_d_1 = 1
                score_ids.append(27)

            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 > 0 and I_1 >= C_1 and C_1 >= S_1:
                i_c_s_1 = 1
                score_ids.append(28)

            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 <= 0 and S_1 >= D_1:
                s_i_1 = 1
                score_ids.append(29)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and S_1 >= I_1:
                s_d_1 = 1
                score_ids.append(30)
            if D_1 > 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and S_1 >= D_1 and D_1 >= I_1:
                s_d_i_1 = 1
                score_ids.append(31)

            if D_1 > 0 and I_1 > 0 and S_1 > 0 and C_1 <= 0 and S_1 >= I_1 and I_1 >= D_1:
                s_i_d_1 = 1
                score_ids.append(32)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 > 0 and S_1 >= I_1 and I_1 >= C_1:
                s_i_c_1 = 1
                score_ids.append(33)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and S_1 >= C_1 and C_1 >= D_1:
                s_c_d_1 = 1
                score_ids.append(34)
            if D_1 <= 0 and I_1 > 0 and S_1 > 0 and C_1 > 0 and S_1 >= C_1 and C_1 >= I_1:
                s_c_i_1 = 1
                score_ids.append(35)
            if D_1 <= 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and C_1 >= I_1:
                c_i_1 = 1
                score_ids.append(36)
            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and C_1 >= D_1 and D_1 >= I_1:
                c_d_i_1 = 1
                score_ids.append(37)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and C_1 >= D_1 and D_1 >= S_1:
                c_d_s_1 = 1
                score_ids.append(38)
            if D_1 > 0 and I_1 > 0 and S_1 <= 0 and C_1 > 0 and C_1 >= I_1 and I_1 >= D_1:
                c_i_d_1 = 1
                score_ids.append(39)
            if D_1 > 0 and I_1 <= 0 and S_1 > 0 and C_1 > 0 and C_1 >= S_1 and S_1 >= D_1:
                c_s_d_1 = 1
                score_ids.append(40)
            line_ids.append((0,0,{'line':1,'c_fields':c_1,'d_fields':d_1,'c_d_fields':c_d_1,'i_d_fields':i_d_1,'i_d_c_fields':i_d_c_1,'i_d_s_fields':i_d_s_1,'i_s_d_fields':i_s_d_1,
                             's_d_c_fields':s_d_c_1,'d_i_fields':d_i_1,'d_i_s_fields':d_i_s_1,'d_s_fields':d_s_1,'c_i_s_fields':c_i_s_1,
                             'c_s_i_fields':c_s_i_1,
                             'i_s_c_i_c_s_fields':i_s_c_i_c_s_1,'s_fields':s_1,'c_s_fields':c_s_1,'s_c_fieds':s_c_1,'d_c_fields':d_c_1,'d_i_c_fields':d_i_c_1,
                             'd_s_i_fields':d_s_i_1,'d_s_c_fields':d_s_c_1,'d_c_i_fields':d_c_i_1,'d_c_s_fields':d_c_s_1,'i_fields':i_1,'i_s_fields':i_s_1,'i_c_fields':i_c_1,
                             'i_c_d_fields':i_c_d_1,'i_c_s_fields':i_c_s_1,'s_d_fields':s_d_1,'s_i_fields':s_i_1,'s_d_i_fields':s_d_i_1,'s_i_d_fields':s_i_d_1,'s_i_c_fields':s_i_c_1,
                             's_c_d_fields':s_c_d_1,'s_c_i_fields':s_c_i_1,'c_i_fields':c_i_1,'c_d_i_fields':c_d_i_1,'c_d_s_fields':c_d_s_1,'c_i_d_fields':c_i_d_1,'c_s_d_fields':c_s_d_1,
                             'match_score':min(score_ids) if score_ids else 0
                             }))



            c_2 = 0
            d_2 = 0
            c_d_2 = 0
            i_d_2 = 0
            i_d_c_2 = 0
            i_d_s_2 = 0
            i_s_d_2 = 0
            s_d_c_2 = 0
            d_c_2 = 0
            d_i_2 = 0
            d_i_s_2 = 0
            d_s_2 = 0
            c_i_s_2 = 0
            c_s_i_2 = 0
            i_s_c_i_c_s_2 = 0
            s_2 = 0
            c_s_2 = 0
            s_c_2 = 0
            d_i_c_2 = 0
            d_s_i_2 = 0
            d_s_c_2 = 0
            d_c_i_2 = 0
            d_c_s_2 =0
            i_2 = 0
            i_s_2 = 0
            i_c_2 = 0
            i_c_d_2 = 0
            i_c_s_2 = 0
            s_i_2 = 0
            s_d_2 = 0
            s_d_i_2 = 0
            s_i_d_2 = 0
            s_i_c_2 = 0
            s_c_d_2 = 0
            s_c_i_2 = 0
            c_i_2 = 0
            c_d_i_2 = 0
            c_d_s_2 = 0
            c_i_d_2 = 0
            c_s_d_2 = 0
            line_2 = record.disc_result_score2_ids.filtered(lambda line:line.line==2)
            D_2 = line_2.d_field
            I_2 = line_2.i_field
            S_2 = line_2.s_field
            C_2 = line_2.c_field

            if D_2 <= 0 and I_2 <= 0 and S_2 <=0 and C_2 > 0:
                c_2 = 1
                score_ids_2.append(1)
            if D_2 > 0 and I_2 <= 0 and S_2 <= 0 and C_2 <= 0:
                d_2 = 1
                score_ids_2.append(2)
            if D_2 > 0 and I_2 <= 0 and S_2 <= 0 and C_2 > 0 and C_2 >= D_2:
                c_d_2 = 1
                score_ids_2.append(3)
            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 <= 0 and I_2 >= D_2:
                i_d_2 = 1
                score_ids_2.append(4)
            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and I_2 >= D_2>= C_2:
                i_d_c_2 = 1
                score_ids_2.append(5)
            if D_2 > 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and I_2 >= D_2 >= S_2:
                i_d_s_2 = 1
                score_ids_2.append(6)
            if D_2 > 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and I_2 >= S_2 >= D_2:
                i_s_d_2 = 1
                score_ids_2.append(7)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and S_2 >= D_2 and D_2 >= C_2:
                s_d_c_2 = 1
                score_ids_2.append(8)
            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 <= 0 and D_2 >= I_2:
                d_c_2 = 1
                score_ids_2.append(9)
            if D_2 > 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and D_2 >= I_2 >= S_2:
                d_i_2 = 1
                score_ids_2.append(10)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 <= 0 and D_2 >=  S_2:
                d_i_s_2 = 1
                score_ids.append(11)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 > 0 and C_2 >= I_2 >= S_2:
                d_s_2 = 1
                score_ids_2.append(12)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 > 0 and C_2 >=  S_2 >= I_2:
                c_i_s_2 = 1
                score_ids_2.append(13)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 > 0 and I_2 >=  S_2 and I_2 >= C_2:
                c_s_i_2 = 1
                score_ids_2.append(14)
            if D_2 <= 0 and I_2 <= 0 and S_2 > 0 and C_2 <= 0:
                i_s_c_i_c_s_2 = 1
                score_ids_2.append(15)
            if D_2 <= 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and C_2 >= S_2:
                s_2 = 1
                score_ids_2.append(16)
            if D_2 <= 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and S_2 >= C_2:
                c_s_2 = 1
                score_ids_2.append(17)
            if D_2 <= 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and D_2 >= C_2:
                s_c_2 = 1
                score_ids_2.append(18)
            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and D_2 >= I_2 >= C_2:
                d_i_c_2 = 1
                score_ids_2.append(19)

            if D_2 > 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and D_2 >= S_2 >= I_2:
                d_s_i_2 = 1
                score_ids_2.append(20)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and D_2 >= S_2 and S_2 >= C_2:
                d_s_c_2 = 1
                score_ids_2.append(21)
            if D_2 > 0 and I_2 >0 and S_2 <= 0 and C_2 > 0 and D_2 >= C_2 and C_2 >= I_2:
                d_c_i_2 = 1
                score_ids_2.append(22)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and D_2 >= C_2 and C_2 >= S_2:
                d_c_s_2 = 1
                score_ids_2.append(23)
            if D_2 <= 0 and I_2 > 0 and S_2 <= 0 and C_2 <= 0:
                i_2 = 1
                score_ids_2.append(24)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and I_2 >= S_2:
                i_s_2 = 1
                score_ids_2.append(25)

            if D_2 <= 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and I_2 >= C_2:
                i_c_2 = 1
                score_ids_2.append(26)


            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and I_2 >= C_2 and C_2 >= D_2:
                i_c_d_2 = 1
                score_ids_2.append(27)

            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 > 0 and I_2 >= C_2 and C_2 >= S_2:
                i_c_s_2 = 1
                score_ids_2.append(28)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 <= 0 and S_2 >= D_2:
                s_i_2 = 1
                score_ids_2.append(29)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and S_2 >= I_2:
                s_d_2 = 1
                score_ids_2.append(30)
            if D_2 > 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and S_2 >= D_2 and D_2 >= I_2:
                s_d_i_2 = 1
                score_ids_2.append(31)

            if D_2 > 0 and I_2 > 0 and S_2 > 0 and C_2 <= 0 and S_2 >= I_2 and I_2 >= D_2:
                s_i_d_2 = 1
                score_ids_2.append(32)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 > 0 and S_2 >= I_2 and I_2 >= C_2:
                s_i_c_2 = 1
                score_ids_2.append(33)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and S_2 >= C_2 and C_2 >= D_2:
                s_c_d_2 = 1
                score_ids_2.append(34)
            if D_2 <= 0 and I_2 > 0 and S_2 > 0 and C_2 > 0 and S_2 >= C_2 and C_2 >= I_2:
                s_c_i_2 = 1
                score_ids_2.append(35)
            if D_2 <= 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and C_2 >= I_2:
                c_i_2 = 1
                score_ids_2.append(36)
            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and C_2 >= D_2 and D_2 >= I_2:
                c_d_i_2 = 1
                score_ids_2.append(37)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and C_2 >= D_2 and D_2 >= S_2:
                c_d_s_2 = 1
                score_ids_2.append(38)
            if D_2 > 0 and I_2 > 0 and S_2 <= 0 and C_2 > 0 and C_2 >= I_2 and I_2 >= D_2:
                c_i_d_2 = 1
                score_ids_2.append(39)
            if D_2 > 0 and I_2 <= 0 and S_2 > 0 and C_2 > 0 and C_2 >= S_2 and S_2 >= D_2:
                c_s_d_2 = 1
                score_ids_2.append(40)
            line_ids.append((0,0,{'line':2,'c_fields':c_2,'d_fields':d_2,'c_d_fields':c_d_2,'i_d_fields':i_d_2,'i_d_c_fields':i_d_c_2,'i_d_s_fields':i_d_s_2,'i_s_d_fields':i_s_d_2,
                             's_d_c_fields':s_d_c_2,'d_i_fields':d_i_2,'d_i_s_fields':d_i_s_2,'d_s_fields':d_s_2,'c_i_s_fields':c_i_s_2,
                             'c_s_i_fields':c_s_i_2,
                             'i_s_c_i_c_s_fields':i_s_c_i_c_s_2,'s_fields':s_2,'c_s_fields':c_s_2,'s_c_fieds':s_c_2,'d_c_fields':d_c_2,'d_i_c_fields':d_i_c_2,
                             'd_s_i_fields':d_s_i_2,'d_s_c_fields':d_s_c_2,'d_c_i_fields':d_c_i_2,'d_c_s_fields':d_c_s_2,'i_fields':i_2,'i_s_fields':i_s_2,'i_c_fields':i_c_2,
                             'i_c_d_fields':i_c_d_2,'i_c_s_fields':i_c_s_2,'s_d_fields':s_d_2,'s_i_fields':s_i_2,'s_d_i_fields':s_d_i_2,'s_i_d_fields':s_i_d_2,'s_i_c_fields':s_i_c_2,
                             's_c_d_fields':s_c_d_2,'s_c_i_fields':s_c_i_2,'c_i_fields':c_i_2,'c_d_i_fields':c_d_i_2,'c_d_s_fields':c_d_s_2,'c_i_d_fields':c_i_d_2,'c_s_d_fields':c_s_d_2,
                             'match_score':min(score_ids_2) if score_ids_2 else 0
                             }))

            c_3 = 0
            d_3 = 0
            c_d_3 = 0
            i_d_3 = 0
            i_d_c_3 = 0
            i_d_s_3 = 0
            i_s_d_3 = 0
            s_d_c_3 = 0
            d_c_3 = 0
            d_i_3 = 0
            d_i_s_3 = 0
            d_s_3 = 0
            c_i_s_3 = 0
            c_s_i_3 = 0
            i_s_c_i_c_s_3 = 0
            s_3 = 0
            c_s_3 = 0
            s_c_3 = 0
            d_i_c_3 = 0
            d_s_i_3 = 0
            d_s_c_3 = 0
            d_c_i_3 = 0
            d_c_s_3 = 0
            i_3 = 0
            i_s_3 = 0
            i_c_3 = 0
            i_c_d_3 = 0
            i_c_s_3 = 0
            s_i_3 = 0
            s_d_3 = 0
            s_d_i_3 = 0
            s_i_d_3 = 0
            s_i_c_3 = 0
            s_c_d_3 = 0
            s_c_i_3 = 0
            c_i_3 = 0
            c_d_i_3 = 0
            c_d_s_3 = 0
            c_i_d_3 = 0
            c_s_d_3 = 0
            line_3 = record.disc_result_score2_ids.filtered(lambda line: line.line == 3)
            D_3 = line_3.d_field
            I_3 = line_3.i_field
            S_3 = line_3.s_field
            C_3 = line_3.c_field

            if D_3 <= 0 and I_3 <= 0 and S_3 <= 0 and C_3 > 0:
                c_3 = 1
                score_ids_3.append(1)
            if D_3 > 0 and I_3 <= 0 and S_3 <= 0 and C_3 <= 0:
                d_3 = 1
                score_ids_3.append(2)
            if D_3 > 0 and I_3 <= 0 and S_3 <= 0 and C_3 > 0 and C_3 >= D_3:
                c_d_3 = 1
                score_ids_3.append(3)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 <= 0 and I_3 >= D_3:
                i_d_3 = 1
                score_ids_3.append(4)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and I_3 >= D_3 >= C_3:
                i_d_c_3 = 1
                score_ids_3.append(5)
            if D_3 > 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and I_3 >= D_3 >= S_3:
                i_d_s_3 = 1
                score_ids_3.append(6)
            if D_3 > 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and I_3 >= S_3 >= D_3:
                i_s_d_3 = 1
                score_ids_3.append(7)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and S_3 >= D_3 and D_3 >= C_3:
                s_d_c_3 = 1
                score_ids_3.append(8)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 <= 0 and D_3 >= I_3:
                d_c_3 = 1
                score_ids_3.append(9)
            if D_3 > 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and D_3 >= I_3 >= S_3:
                d_i_3 = 1
                score_ids_3.append(10)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 <= 0 and D_3 >= S_3:
                d_i_s_3 = 1
                score_ids_3.append(11)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 > 0 and C_3 >= I_3 >= S_3:
                d_s_3 = 1
                score_ids_3.append(12)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 > 0 and C_3 >= S_3 >= I_3:
                c_i_s_3 = 1
                score_ids_3.append(13)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 > 0 and I_3 >= S_3 and I_3 >= C_3:
                c_s_i_3 = 1
                score_ids_3.append(14)
            if D_3 <= 0 and I_3 <= 0 and S_3 > 0 and C_3 <= 0:
                i_s_c_i_c_s_3 = 1
                score_ids_3.append(15)
            if D_3 <= 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and C_3 >= S_3:
                s_3 = 1
                score_ids_3.append(16)
            if D_3 <= 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and S_3 >= C_3:
                c_s_3 = 1
                score_ids_3.append(17)
            if D_3 > 0 and I_3 <= 0 and S_3 <= 0 and C_3 > 0 and D_3 >= C_3:
                s_c_3 = 1
                score_ids_3.append(18)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and D_3 >= I_3 >= C_3:
                d_i_c_3 = 1
                score_ids_3.append(19)

            if D_3 > 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and D_3 >= S_3 >= I_3:
                d_s_i_3 = 1
                score_ids_3.append(20)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and D_3 >= S_3 and S_3 >= C_3:
                d_s_c_3 = 1
                score_ids_3.append(21)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and D_3 >= C_3 and C_3 >= I_3:
                d_c_i_3 = 1
                score_ids_3.append(22)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and D_3 >= C_3 and C_3 >= S_3:
                d_c_s_3 = 1
                score_ids_3.append(23)
            if D_3 <= 0 and I_3 > 0 and S_3 <= 0 and C_3 <= 0 :
                i_3 = 1
                score_ids_3.append(24)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and I_3 >= S_3:
                i_s_3 = 1
                score_ids_3.append(25)

            if D_3 <= 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and I_3 >= C_3:
                i_c_3 = 1
                score_ids_3.append(26)

            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and I_3 >= C_3 and C_3 >= D_3:
                i_c_d_3 = 1
                score_ids_3.append(27)

            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 > 0 and I_3 >= C_3 and C_3 >= S_3:
                i_c_s_3 = 1
                score_ids_3.append(28)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 <= 0 and S_3 >= D_3:
                s_i_3 = 1
                score_ids_3.append(29)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and S_3 >= I_3:
                s_d_3 = 1
                score_ids_3.append(30)
            if D_3 > 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and S_3 >= D_3 and D_3 >= I_3:
                s_d_i_3 = 1
                score_ids_3.append(31)

            if D_3 > 0 and I_3 > 0 and S_3 > 0 and C_3 <= 0 and S_3 >= I_3 and I_3 >= D_3:
                s_i_d_3 = 1
                score_ids_3.append(32)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 > 0 and S_3 >= I_3 and I_2 >= C_3:
                s_i_c_3 = 1
                score_ids_3.append(33)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and S_3 >= C_3 and C_3 >= D_3:
                s_c_d_3 = 1
                score_ids_3.append(34)
            if D_3 <= 0 and I_3 > 0 and S_3 > 0 and C_3 > 0 and S_3 >= C_3 and C_3 >= I_3:
                s_c_i_3 = 1
                score_ids_3.append(35)
            if D_3 <= 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and C_3 >= I_3:
                c_i_3 = 1
                score_ids_3.append(36)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and C_3 >= D_3 and D_3 >= I_3:
                c_d_i_3 = 1
                score_ids_3.append(37)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and C_3 >= D_3 and D_3 >= S_3:
                c_d_s_3 = 1
                score_ids_3.append(38)
            if D_3 > 0 and I_3 > 0 and S_3 <= 0 and C_3 > 0 and C_3 >= I_3 and I_3 >= D_3:
                c_i_d_3 = 1
                score_ids_2.append(39)
            if D_3 > 0 and I_3 <= 0 and S_3 > 0 and C_3 > 0 and C_3 >= S_3 and S_3 >= D_3:
                c_s_d_3 = 1
                score_ids_3.append(40)
            line_ids.append((0, 0,
                             {'line': 3, 'c_fields': c_3, 'd_fields': d_3, 'c_d_fields': c_d_3, 'i_d_fields': i_d_3,
                              'i_d_c_fields': i_d_c_3, 'i_d_s_fields': i_d_s_3, 'i_s_d_fields': i_s_d_3,
                              's_d_c_fields': s_d_c_3, 'd_i_fields': d_i_3, 'd_i_s_fields': d_i_s_3,
                              'd_s_fields': d_s_3, 'c_i_s_fields': c_i_s_3,
                              'c_s_i_fields': c_s_i_3,
                              'i_s_c_i_c_s_fields': i_s_c_i_c_s_3, 's_fields': s_3, 'c_s_fields': c_s_3,
                              's_c_fieds': s_c_3, 'd_c_fields': d_c_3, 'd_i_c_fields': d_i_c_3,
                              'd_s_i_fields': d_s_i_3, 'd_s_c_fields': d_s_c_3, 'd_c_i_fields': d_c_i_3,
                              'd_c_s_fields': d_c_s_3, 'i_fields': i_3, 'i_s_fields': i_s_3, 'i_c_fields': i_c_3,
                              'i_c_d_fields': i_c_d_3, 'i_c_s_fields': i_c_s_3, 's_d_fields': s_d_3,
                              's_i_fields': s_i_3, 's_d_i_fields': s_d_i_3, 's_i_d_fields': s_i_d_3,
                              's_i_c_fields': s_i_c_3,
                              's_c_d_fields': s_c_d_3, 's_c_i_fields': s_c_i_3, 'c_i_fields': c_i_3,
                              'c_d_i_fields': c_d_i_3, 'c_d_s_fields': c_d_s_3, 'c_i_d_fields': c_i_d_3,
                              'c_s_d_fields': c_s_d_3,
                              'match_score': min(score_ids_3) if score_ids_3 else 0
                              }))


            record.disc_result_score3_ids = line_ids


    def generate_final_score(self):
        for record in self:
            if record.disc_result_score3_ids:
                line_1 = record.disc_result_score3_ids.filtered(lambda line:line.line == 1)
                line_2 = record.disc_result_score3_ids.filtered(lambda line:line.line == 2)
                line_3 = record.disc_result_score3_ids.filtered(lambda line:line.line == 3)
                mask_public_self = self.env['survey.disc.variables'].search([('sequence','=',line_1.match_score)])
                if mask_public_self:
                    record.mask_public_self = mask_public_self.id
                core_private_self = self.env['survey.disc.variables'].search([('sequence','=',line_2.match_score)])
                if core_private_self:
                    record.core_private_self = core_private_self.id
                mirror_perceived_self = self.env['survey.disc.variables'].search([('sequence', '=', line_3.match_score)])
                if mirror_perceived_self:
                    record.mirror_perceived_self = mirror_perceived_self.id


    def generate_ist_score(self):
        age = 0
        score_se = 0
        score_wa = 0
        score_an = 0
        score_ge = 0
        score_ra = 0
        score_zr = 0
        score_fa = 0
        score_wu = 0
        score_me = 0

        rw_list = []
        category_list = []
        sw_list = []
        parameter_list = []
        parameter_name_list = []
        parameter_desc_list = []
        
        for record in self:
            applicant = self.env['hr.applicant'].browse(record.applicant_id.id)
            age += applicant.birth_years
            for input_user in record.user_input_line_ids:
                for question_id in input_user.question_id:
                    datas = self.env['survey.question'].search([('title', '=', question_id.title)])
                    if datas:
                        for data in datas:
                            for answer in data.suggested_answer_ids:
                                if input_user.answer_type == 'suggestion':
                                    if answer.is_correct:
                                        for suggested_answer_id in input_user.suggested_answer_id:
                                            if answer.value == suggested_answer_id.value:
                                                input_user.answer_score = answer.answer_score
                                                print("==========: ", data.code_ist)
                                                if data.code_ist == "se":
                                                    score_se += input_user.answer_score
                                                elif data.code_ist == "an":
                                                    score_an += input_user.answer_score
                                                elif data.code_ist == "wa":
                                                    score_wa += input_user.answer_score
                                                elif data.code_ist == "fa":
                                                    score_fa += input_user.answer_score
                                                elif data.code_ist == "wu":
                                                    score_wu += input_user.answer_score
                                                elif data.code_ist == "me":
                                                    score_me += input_user.answer_score

                                elif input_user.answer_type == 'char_box':
                                    if answer.is_correct:
                                        if answer.value == input_user.value_char_box.lower():
                                            input_user.answer_score = answer.answer_score

                                            if data.code_ist == "ge":
                                                    score_ge += input_user.answer_score
                                
                                elif input_user.answer_type == 'numerical_box':
                                    print(float(answer.value))
                                    if answer.is_correct:
                                        if float(answer.value) == float(input_user.value_numerical_box):
                                            input_user.answer_score = answer.answer_score

                                            if data.code_ist == "ra":
                                                    score_ra += input_user.answer_score
                                            elif data.code_ist == "zr":
                                                    score_zr += input_user.answer_score

            # Convert score GE
            record.convert_ge_score(score_ge)

            ist_scoring_result_nonmatrix = self.env['ist.scoring.result.nonmatrix'].search([
                ('id', '=', record.ist_scoring_result_nonmatrix_ids.id)
            ])

            if ist_scoring_result_nonmatrix:
                for score in ist_scoring_result_nonmatrix:
                    score.score_se = score_se
                    score.score_wa = score_wa
                    score.score_an = score_an
                    # score.score_ge = score_ge
                    score.score_ra = score_ra
                    score.score_zr = score_zr
                    score.score_fa = score_fa
                    score.score_wu = score_wu
                    score.score_me = score_me

                    rw_list.append(score.score_se)
                    rw_list.append(score.score_wa)
                    rw_list.append(score.score_an)
                    rw_list.append(score.score_ge_converted)
                    rw_list.append(score.score_ra)
                    rw_list.append(score.score_zr)
                    rw_list.append(score.score_fa)
                    rw_list.append(score.score_wu)
                    rw_list.append(score.score_me)

            
            record.compare_ist_score_code_by_age(age)
            record.generate_gesamt_score(age)

            for sw_score in record.ist_scoring_result_matrix_by_age_ids:
                sw_list.append(sw_score.score_se)
                sw_list.append(sw_score.score_wa)
                sw_list.append(sw_score.score_an)
                sw_list.append(sw_score.score_ge)
                sw_list.append(sw_score.score_ra)
                sw_list.append(sw_score.score_zr)
                sw_list.append(sw_score.score_fa)
                sw_list.append(sw_score.score_wu)
                sw_list.append(sw_score.score_me)


            categories = self.env['ist.scoring.category'].search([])
            for score in sw_list:    
                for category in categories:
                    if score >= category.score_from and score <= category.score_to:
                        category_list.append(category.name)

            parameters = self.env['ist.parameter.root'].search([])
            for parameter in parameters:
                parameter_list.append(parameter.code)
                parameter_name_list.append(parameter.parameter)
                parameter_desc_list.append(parameter.description)

            for i in range(len(sw_list)):
                record.ist_scoring_result_ids = [(0,0,{
                                                    'parameter': parameter_name_list[i],
                                                    'code': parameter_list[i],
                                                    'rw': rw_list[i],
                                                    'sw': sw_list[i],
                                                    'description': parameter_desc_list[i],
                                                    'category': category_list[i]
                                                })]



    def convert_ge_score(self, score):
        for record in self:
            ge_conversion = self.env['ist.ge.conversion'].search([('name', '=', 'GE')])
            converted_score = 0.0
            for ge in ge_conversion:
                for line in ge.ist_ge_conversion_line_ids:
                    if score == line.actual_score:
                        converted_score += line.converted_score
            
            record.ist_scoring_result_nonmatrix_ids = [(0,0,{
                                                'score_ge_converted': converted_score,
                                                })]
        
        return converted_score
    
    
    
    def compare_ist_score_code_by_age(self, age):
        ist_scoring_matrix = self.env['ist.scoring.matrix'].search([])

        final_score_se = 0.0
        final_score_wa = 0.0
        final_score_an = 0.0
        final_score_ge = 0.0
        final_score_ra = 0.0
        final_score_zr = 0.0
        final_score_fa = 0.0
        final_score_wu = 0.0
        final_score_me = 0.0

        for record in self:
            for matrix in ist_scoring_matrix:
                if age >= matrix.age_from and age <= matrix.age_to:
                    for matrix_line in matrix.ist_age_line_ids:
                        for score_code in record.ist_scoring_result_nonmatrix_ids:
                            if matrix_line.score == score_code.score_se:
                                final_score_se += matrix_line.satzerganzng
                            if matrix_line.score == score_code.score_wa:
                                final_score_wa += matrix_line.worthausuahi
                            if matrix_line.score == score_code.score_an:
                                final_score_an += matrix_line.analogien
                            if matrix_line.score == score_code.score_ge_converted:
                                final_score_ge += matrix_line.gmeisamkeiten
                            if matrix_line.score == score_code.score_ra:
                                final_score_ra += matrix_line.rachen_aufgaben
                            if matrix_line.score == score_code.score_zr:
                                final_score_zr += matrix_line.zahlen_reihen
                            if matrix_line.score == score_code.score_fa:
                                final_score_fa += matrix_line.form_ausuahi
                            if matrix_line.score == score_code.score_wu:
                                final_score_wu += matrix_line.wurfal_augaben
                            if matrix_line.score == score_code.score_me:
                                final_score_me += matrix_line.merk_aufgaben 

        record.ist_scoring_result_matrix_by_age_ids = [(0,0,{
                                                'score_se': final_score_se,
                                                'score_wa': final_score_wa,
                                                'score_an': final_score_an,
                                                'score_ge': final_score_ge,
                                                'score_ra': final_score_ra,
                                                'score_zr': final_score_zr,
                                                'score_fa': final_score_fa,
                                                'score_wu': final_score_wu,
                                                'score_me': final_score_me,
                                                })]
        
        return final_score_se, final_score_wa, final_score_an, final_score_ge, final_score_ra, final_score_zr, final_score_fa, final_score_wu, final_score_me
    

    def generate_gesamt_score(self, age):
        ist_scoring_gesamt = self.env['ist.scoring.gesamt'].search([])
        gesamt_score = 0.0
        total_row_score = 0.0
        iq_score = 0.0
        iq_category = ""
        iq_dominance_score = 0
        iq_dominance_category = ""
        mindset = []
        is_verbal_teoritis = False
        mindset_descriptions = []

        for record in self:
            for score_code in record.ist_scoring_result_nonmatrix_ids:
                total_rs = score_code.score_se + score_code.score_wa + score_code.score_an + score_code.score_ge_converted + score_code.score_ra + score_code.score_zr + score_code.score_fa + score_code.score_wu + score_code.score_me

                total_row_score += total_rs

            for gesamt in ist_scoring_gesamt:
                if age >= gesamt.age_from and age <= gesamt.age_to:
                    for matrix_line in gesamt.line_ids:
                            if matrix_line.row_score == total_row_score:
                                gesamt_score += matrix_line.score                            

            ist_scoring_iq = self.env['ist.scoring.iq'].search([])
            for line in ist_scoring_iq:
                if gesamt_score == line.score:
                    iq_score += line.iq
            
            ist_iq_category = self.env['ist.scoring.iq.category'].search([])
            for category in ist_iq_category:
                if total_row_score >= category.score_from and total_row_score <= category.score_to:
                    iq_category += category.name
            
            for sw_score in record.ist_scoring_result_matrix_by_age_ids:
                ge_ra = sw_score.score_ge + sw_score.score_ra
                an_zr = sw_score.score_an + sw_score.score_zr

                if ge_ra > an_zr:
                    iq_dominance_score += ge_ra - an_zr
                else:
                    iq_dominance_score += an_zr - ge_ra
                
                if sw_score.score_se < sw_score.score_wa:
                    is_verbal_teoritis = True
                
                elif sw_score.score_se > sw_score.score_wa:
                    is_verbal_teoritis = False
            
            iq_dominances = self.env['ist.scoring.iq.dominance'].search([])
            for dominance in iq_dominances:
                if iq_dominance_score >= dominance.score_from and iq_dominance_score <= dominance.score_to:
                    mindset.append(dominance.name)
                    mindset_descriptions.append(dominance.description)
            
            mindset_profiles = self.env['ist.mindset.profile'].search([])
            for profile in mindset_profiles:
                if is_verbal_teoritis == profile.is_verbal_teoritis:
                    mindset.append(profile.name)
                    mindset_descriptions.append(profile.description)
            
            mindset_profile_category = ['Corak Berfikir', 'Cara Berfikir']
            
            record.ist_scoring_final_result_ids = [(0,0,{
                                                'total_rw': total_row_score,
                                                'gesamt_score': gesamt_score,
                                                'iq_score': iq_score,
                                                'iq_category': iq_category,
                                                })]

            for i in range(len(mindset_profile_category)):
                record.ist_mindset_profile_final_result_ids = [(0,0,{
                                                    'category': mindset_profile_category[i],
                                                    'result': mindset[i],
                                                    'description': mindset_descriptions[i],
                                                    })]
            
        return total_row_score, gesamt_score, iq_category, iq_score


    @api.depends('survey_id')
    def _get_survey_type(self):
        for record in self:
            if record.survey_id:
                record.survey_type = str(record.survey_id.survey_type).upper()
            else:
                record.survey_type = False
    def save_lines_files(self,question, answer,filename, comment=None):
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question)
        ])
        
        self._save_file(question, old_answers,filename,answer, comment)


    def save_lines_videofiles(self,question, answer,filename,applicant_id=False, comment=None):
        module_path = get_module_path('equip3_hr_survey_extend')
        que_obj = self.env['survey.question'].sudo()
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),('create_uid','=',self.env.user.id),
            ('question_id', '=', question)
        ])
        old_answers.unlink()
        data_que = que_obj.browse(question)
        applicant = False
        if applicant_id:
            applicant = self.env['hr.applicant'].sudo().browse(applicant_id)
        YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_VERSION = "v3"
        creds = None
        refresh_token =  self.env['ir.config_parameter'].sudo().get_param("equip3_hr_survey_extend.refresh_token")
        if refresh_token:
            creds = Credentials.from_authorized_user_info(eval(refresh_token), YOUTUBE_UPLOAD_SCOPE)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                refresh_token =  self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.refresh_token",creds.to_json())

        # credentials = AccessTokenCredentials(self.env.user.company_id.youtube_access_token, "MyAgent/1.0", None)
          

        decoded_data = base64.b64decode(answer)
        mimetype = guess_mimetype(decoded_data)

        binaryimage = answer.encode("ascii")
        binaryimage = base64.decodebytes(binaryimage)
        fpath =  module_path + "/googletoken/"
        if not os.path.isdir(fpath):
            os.mkdir(fpath)
        filename_video = fpath +self.env.user.name+" ("+self.survey_id.display_name+")"+".webm"
        with open(filename_video, 'wb') as wfile:
           wfile.write(decoded_data)
        cap = cv2.VideoCapture(filename_video)

        

        success, frame = cap.read()

        service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)  
        privacyStatus = 'unlisted'
        youtube_desc = data_que.title
        youtube_uploaded_date = datetime.now()
        applicant_email = applicant_name = applied_job = '-'
        if applicant:
            applicant_name = applicant.partner_name or '-'
            applicant_email = applicant.email_from or '-'
            applied_job = applicant.job_id.name or '-'

        else:
            applicant_name = self.env.user.name or '-'
            applicant_email = self.env.user.email or '-'

        name_title = applied_job + "/" + applicant_name + "/" + applicant_email
        request = service.videos().insert(
            part="snippet,status,contentDetails,statistics",
            body={
              "snippet": {
                "title": name_title ,
                'description':youtube_desc,
              },
              "status":{'privacyStatus':privacyStatus}
            },
            media_body=MediaFileUpload(fpath+self.env.user.name+" ("+self.survey_id.display_name+")"+".webm")
        )
  
        response = request.execute()
 
        youtube_url = "https://www.youtube.com/embed/"+str(response['id'])
        youtube_watch = "http://www.youtube.com/watch?v="+str(response['id'])
        print(youtube_watch,'youtube_watchyoutube_watch')

        yt_length = YouTube(youtube_watch)  ## this creates a YOUTUBE OBJECT
        try:
            youtube_durations = yt_length.length
            print(youtube_durations,'youtube_durations1111111111')
            youtube_durations = str(datetime1.timedelta(seconds=youtube_durations))
            print(youtube_durations,'youtube_durations333333333')
        except:
            youtube_durations = False

        youtube_title = response['snippet']['title']
        youtube_visibility = privacyStatus

        self.env['survey.user_input.line'].create({
            'question_id':question,
            'youtube_url':youtube_url,
            'youtube_title':youtube_title,
            'youtube_desc':youtube_desc,
            'youtube_visibility':youtube_visibility,
            'youtube_durations':youtube_durations,
            'youtube_uploaded_date':youtube_uploaded_date,
            'answer_type':'video',
            'value_video':'video',
            'user_input_id':self.id
            })
        os.remove(fpath+self.env.user.name+" ("+self.survey_id.display_name+")"+".webm")


    def save_lines(self, question, answer, comment=None):
        """ Save answers to questions, depending on question type

            If an answer already exists for question and user_input_id, it will be
            overwritten (or deleted for 'choice' questions) (in order to maintain data consistency).
        """
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])

        if question.question_type in ['char_box', 'text_box', 'numerical_box', 'date', 'datetime']:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({'email': answer})
            if question.save_as_nickname and answer:
                self.write({'nickname': answer})

        elif question.question_type in ['simple_choice', 'multiple_choice','epps', 'papikostick', 'mbti', 'vak']:
            self._save_line_choice(question, old_answers, answer, comment)
        elif question.question_type == 'matrix':
            self._save_line_matrix(question, old_answers, answer, comment)

        elif question.question_type == 'disc':
            self._save_line_disc(question, old_answers, answer, comment)
        elif question.question_type == 'ist':
            if question.ist_sub_type == 'simple_choice':
                self._save_line_choice(question, old_answers, answer, comment)
            elif question.ist_sub_type in ['char_box', 'numerical_box']:
                vals = self._save_line_simple_answer_ist(question, old_answers, answer)
                if question.save_as_email and answer:
                    self.write({'email': answer})
                if question.save_as_nickname and answer:
                    self.write({'nickname': answer})
                
        elif question.question_type == 'file':
            pass

        elif question.question_type == 'video':
            pass

        elif question.question_type == 'kraepelin':
            pass
            
        else :
            raise AttributeError(question.question_type + ": This type of question has no saving function")
        
        
    def _save_file(self,question, old_answers, filename,answers, comment):
        old_answers.sudo().unlink()    
        return self.env['survey.user_input.line'].create({'question_id':question,'file':answers,'user_input_id':self.id,'filename':filename})


    def _get_line_answer_values_ist(self, question, answer, answer_type):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals

        if answer_type == 'suggestion':
            vals['suggested_answer_id'] = int(answer)
        elif answer_type == 'numerical_box':
            vals['value_numerical_box'] = float(answer)
        else:
            vals['value_%s' % answer_type] = answer.lower()
        return vals


    def _save_line_simple_answer_ist(self, question, old_answers, answer):
        vals = self._get_line_answer_values_ist(question, answer, question.ist_sub_type)
        if old_answers:
            old_answers.write(vals)
            return old_answers
        else:
            return self.env['survey.user_input.line'].create(vals)


    def _save_line_choice(self, question, old_answers, answers, comment):
        if not (isinstance(answers, list)):
            answers = [answers]
        vals_list = []

        if question.question_type == 'simple_choice':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'epps':
            vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'multiple_choice':
            vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'papikostick':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'ist':
            if question.ist_sub_type == 'simple_choice':
                if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                    vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'mbti':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'vak':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)


    def _save_line_disc(self, question, old_answers, answers, comment):
        vals_list = []

        if answers:
            for row_key, row_answer in answers.items():
                for answer in row_answer:
                    vals = self._get_line_answer_values(question, answer, 'suggestion')
                    vals['matrix_row_id'] = int(row_key)
                    vals['disc_row_id'] = int(row_key)
                    vals_list.append(vals.copy())

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

class equip3SurveyEppsConsistencyResult(models.Model):
    _name = 'survey.consistency.result'
    survey_user_input =  fields.Many2one('survey.user_input')
    factor = fields.Char()
    c1 = fields.Integer()
    c2 = fields.Integer()
    c3 = fields.Integer()
    c4 = fields.Integer()
    c5 = fields.Integer()
    c6 = fields.Integer()
    c7 = fields.Integer()
    c8 = fields.Integer()
    c9 = fields.Integer()
    c10 = fields.Integer()
    c11 = fields.Integer()
    c12 = fields.Integer()
    c13 = fields.Integer()
    c14 = fields.Integer()
    c15 = fields.Integer()
    score = fields.Integer()
    percentile = fields.Integer()
    category = fields.Char()
    


class equip3SurveyInterviewSkillsResult(models.Model):
    _name = 'survey.interview.skill.result'
    survey_user_input =  fields.Many2one('survey.user_input')
    question = fields.Char()
    comment = fields.Char()
    score = fields.Selection([('0','Zero'),('1','Worst'),('2','Poor'),('3','Average'),('4','Good'),('5','Excellent')])
    
class equip3SurveyInterviewPersonalitysResult(models.Model):
    _name = 'survey.interview.personality.result'
    survey_user_input =  fields.Many2one('survey.user_input')
    question = fields.Char()
    comment = fields.Char()
    score = fields.Selection([('0','Zero'),('1','Worst'),('2','Poor'),('3','Average'),('4','Good'),('5','Excellent')])
    
    
class equip3SurveyEppsPersonalityResult(models.Model):
    _name = 'survey.personality.result'
    survey_user_input =  fields.Many2one('survey.user_input')
    factor = fields.Char()
    r1 = fields.Integer()
    r2 = fields.Integer()
    r3 = fields.Integer()
    r4 = fields.Integer()
    r5 = fields.Integer()
    r6 = fields.Integer()
    r7 = fields.Integer()
    r8 = fields.Integer()
    r9 = fields.Integer()
    r10 = fields.Integer()
    r11 = fields.Integer()
    r12 = fields.Integer()
    r13 = fields.Integer()
    r14 = fields.Integer()
    r = fields.Integer()
    
    c1 = fields.Integer()
    c2 = fields.Integer()
    c3 = fields.Integer()
    c4 = fields.Integer()
    c5 = fields.Integer()
    c6 = fields.Integer()
    c7 = fields.Integer()
    c8 = fields.Integer()
    c9 = fields.Integer()
    c10 = fields.Integer()
    c11 = fields.Integer()
    c12 = fields.Integer()
    c13 = fields.Integer()
    c14 = fields.Integer()
    c = fields.Integer()
    rs = fields.Integer()
    
    description = fields.Text()
    x_description_limited = fields.Text(compute="_compute_x_description_limited", store=True)
    percentile = fields.Integer()
    category = fields.Char()
    
    
    
    @api.depends('description')
    def _compute_x_description_limited(self):
        for record in self:
            if record.description:
                if len(record.description) > 60:
                    record['x_description_limited'] = f"{record.description[:60]}..."
                else:
                    record['x_description_limited'] = record.description
            else:
                record['x_description_limited'] = False
    
    
    
class Equip3SurveyInheritSurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'
    _order = 'question_id'
    ## temporary comment unknown comodel_name survey.question.master.answer
    disc_row_id = fields.Many2one('survey.question.answer', string="Row answer")
    code = fields.Char("Code",compute='_get_code')
    is_skip = fields.Boolean(default=False)
    is_hide_code = fields.Boolean(default=False,compute='_get_survey_type')
    file  = fields.Binary()
    filename = fields.Char()
    youtube_url = fields.Char("Answer Video")
    youtube_title = fields.Char("Youtube Title")
    youtube_desc = fields.Char("Youtube Desc")
    youtube_visibility = fields.Char("Youtube Visibility")
    youtube_durations = fields.Char("Youtube Durations")
    youtube_uploaded_date = fields.Datetime("Youtube Uploaded Date")
    is_youtube_open_video = fields.Boolean("is_youtube_open_video",copy=False)
    is_score_editable = fields.Boolean(compute='_compute_is_score_editable')
    answer_type = fields.Selection(selection_add=[('video', 'Video'),('numerical_box',)], ondelete={'video': 'cascade'},
        string='Answer Type')
    value_video = fields.Char('value_video')
    
    mbti_code = fields.Selection(selection=[
        ('e', 'E'),
        ('f', 'F'),
        ('i', 'I'),
        ('j', 'J'),
        ('n', 'N'),
        ('p', 'P'),
        ('s', 'S'),
        ('t', 'T')
    ], string="Code", compute="_compute_get_mbti_code", store=True)
    vak_selection = fields.Selection([('v','V'),('a','A'),('k','K')],string="Code",related='suggested_answer_id.vak_selection',store=True)


    
    @api.depends('suggested_answer_id')
    def _compute_get_mbti_code(self):
        for question in self:
            if question.suggested_answer_id:
                question.mbti_code = question.suggested_answer_id.mbti_code



    def youtube_popup_video_wizard_action(self):
        return {
                'name': _('Open Video'),
                'view_type': 'form',
                'view_mode': 'form',
                'target' : 'new',
                'res_model': 'youtube.popup.video.wizard',
                'view_id': False,
                'views': [(self.env.ref('equip3_hr_survey_extend.youtube_popup_video_wizard_view_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        obj = self.env['survey.user_input.line']
        datayutube = obj.search([('youtube_url','!=',False),('youtube_durations','=','0:00:00')])
        for i in datayutube:
            youtube_url = i.youtube_url
            youtube_id = youtube_url.replace("https://www.youtube.com/embed/",'')
            video = "http://www.youtube.com/watch?v="+youtube_id
            yt = YouTube(video)
            try:
                video_length = yt.length 
                youtube_durations = str(datetime1.timedelta(seconds=video_length))
                i.write({'youtube_durations':youtube_durations})
            except:
                pass

        result = super(Equip3SurveyInheritSurveyUserInputLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return result

    def get_open_video_yutub(self):
        self.is_youtube_open_video = True
  

    def get_close_video_yutub(self):
        self.is_youtube_open_video = False
      

    def unlink(self):
        for data in self:
            if data.youtube_url:

                YOUTUBE_API_SERVICE_NAME = "youtube"
                YOUTUBE_API_VERSION = "v3"
                youtube_id = data.youtube_url.replace('https://www.youtube.com/embed/','')
                credentials = AccessTokenCredentials(self.env.user.company_id.youtube_access_token, "MyAgent/1.0", None)
                service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)  
                request = service.videos().delete(
                    id=youtube_id
                )
                # response = request.execute()
                # print(response,'responseresponse')
                try:
                    response = request.execute()
                except:
                    print('aaaaaaaa')

        result = super(Equip3SurveyInheritSurveyUserInputLine, self).unlink()
        return result

    def _get_survey_type(self):
        for record in self:
            if record.user_input_id:
                if record.user_input_id.survey_type != 'DISC':
                    record.is_hide_code = True
                else:
                    record.is_hide_code =False
            else:
                record.is_hide_code = False


    def _compute_is_score_editable(self):
        for record in self:
            if record.question_id.question_type in ['text_box', 'char_box', 'file']:
                record.is_score_editable = True
            else:
                record.is_score_editable = False



    @api.depends('user_input_id','suggested_answer_id','matrix_row_id')
    def _get_code(self):
        for record in self:
            if record.user_input_id.survey_type =='DISC' and record.suggested_answer_id and record.matrix_row_id:

                if str(record.suggested_answer_id.value).upper() == 'M' and not record.is_skip:
                    record.code = str(record.matrix_row_id.code_m)
                elif str(record.suggested_answer_id.value).upper() == 'L' and not record.is_skip:
                    record.code = str(record.matrix_row_id.code_l)
                elif str(record.suggested_answer_id.value).upper() == 'M' and  record.is_skip:
                    record.code = "*"
                elif str(record.suggested_answer_id.value).upper() == 'L' and  record.is_skip:
                    record.code = "*"
                else:
                    record.code = "*"
            else:
                record.code = "*"

class surveyInputPersonalityLine(models.Model):
    _name = 'survey.input.personality.line'
    mask_public_self = fields.Many2one('survey.user_input')
    core_private_self = fields.Many2one('survey.user_input')
    mirror_perceived_self = fields.Many2one('survey.user_input')
    personality = fields.Char()
    personality_en = fields.Char()
    
    
class surveyVakScore(models.Model):
    _name = 'survey.input.vak.score'
    
    survey_user_input_id =  fields.Many2one('survey.user_input')
    vak_code = fields.Char()
    total = fields.Integer()
    percentage = fields.Integer()
    interpretation = fields.Selection([('dominan','Dominan'),('sekunder','Sekunder'),('non_dominan','Kurang Dominan')])
    




