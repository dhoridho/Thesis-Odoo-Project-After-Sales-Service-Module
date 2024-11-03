# -*- coding: utf-8 -*-
# from odoo import http


import json
import logging
import werkzeug
import odoo
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.modules import get_module_path
from odoo import fields, http, _
from odoo.addons.base.models.ir_ui_view import keep_query
from odoo.exceptions import UserError
from odoo.http import request, content_disposition
from odoo.osv import expression
import requests
import json
import base64
import math
import plotly
import plotly.graph_objs as go
import os
import google_auth_oauthlib.flow
from google.auth.transport.requests import AuthorizedSession
from odoo.addons.survey.controllers.main import Survey as SurveyController

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'


def get_last_digit(number):
    num_str = str(number)
    if len(num_str) > 1:
        return int(num_str[-1])
    else:
        return number


class Survey(http.Controller):

    # ------------------------------------------------------------
    # ACCESS
    # ------------------------------------------------------------

    @http.route('/auth-token-youtube', type='http', auth="public", csrf=False, website=True)
    def auth_token_youtube(self, **post):
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        module_path = get_module_path('equip3_hr_survey_extend')
        client_config = request.env['ir.config_parameter'].sudo().get_param("equip3_hr_survey_extend.client_config")
        flow = google_auth_oauthlib.flow.Flow.from_client_config(eval(client_config), scopes=post.get('scope'),
                                                                 state=post.get('state'))
        flow.redirect_uri = f"{base_url}/auth-token-youtube"
        flow.fetch_token(code=post.get('code'))
        credentials = flow.credentials
        user_info_endpoint = 'https://www.googleapis.com/oauth2/v1/userinfo'
        session = AuthorizedSession(credentials)
        user_info_response = session.get(user_info_endpoint)
        user_info = user_info_response.json()
        request.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.user_name",
                                                            user_info['name'] or False)
        request.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.email_login",
                                                            user_info['email'] or False)
        request.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.is_valid_youtube", True)
        request.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.access_token", credentials.token)
        request.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.refresh_token",
                                                            credentials.to_json())
        action = request.env.ref('equip3_hr_survey_extend.youtube_res_config_settings_act')
        view_id = request.env.ref('equip3_hr_survey_extend.youtube_res_config_settings_form_view')
        return http.redirect_with_hash(f'/web#id=&view_type=form&model=res.config.settings&action={action.id}')

    @http.route('/interview/save/videofile', type='json', auth='public', website=True)
    def interview_save_videofile(self, **post):
        answer = post.get('base64')
        decoded_data = base64.b64decode(answer)
        module_path = get_module_path('equip3_hr_survey_extend')
        fpath = module_path + "/googletoken/"
        if not os.path.isdir(fpath):
            os.mkdir(fpath)
        filename_video = fpath + request.env.user.name + f"{datetime.now()} (Question Interview Video).webm"
        with open(filename_video, 'wb') as wfile:
            wfile.write(decoded_data)

    @http.route('/survey/save/kraepelin', type='json', auth='public', website=True)
    def survey_save_kraepelin(self, **post):
        question_array = post.get('question_array')
        answer_array = post.get('answer_array')
        new_question_array = []
        new_answer_array = []
        correct_answers = []
        kraepelin_panker_dict = {}
        kraepelin_tianker_dict = {}
        kraepelin_janker_dict = {}
        kraepelin_hanker_dict = {}

        if question_array and answer_array:
            survey_user_input = request.env['survey.user_input'].search(
                [('access_token', '=', post.get('access_token'))])
            kraepelin_id = request.env.ref('equip3_hr_survey_extend.survey_root_kraepelin_master').id
            survey_kraepelin = request.env['survey.survey'].search([('id', '=', kraepelin_id)])

            kraepelin_question_columns = survey_kraepelin.kraepelin_columns
            kraepelin_time_per_columns = survey_kraepelin.kraepelin_time_per_column
            kraepelin_question_rows = survey_kraepelin.kraepelin_rows

            for i in range(0, len(question_array), kraepelin_question_rows):
                new_question_array.append(question_array[i:i + kraepelin_question_rows])

            # Get correct answers from questions
            for arr in new_question_array:
                integer_arr = [int(x) for x in arr]
                for i in range(len(integer_arr) - 1):
                    integer_arr[i] += integer_arr[i + 1]
                integer_arr.pop()
                correct_answers.append(integer_arr)

            kraepelin_answer_rows = survey_kraepelin.kraepelin_rows - 1
            for i in range(0, len(answer_array), kraepelin_answer_rows):
                new_answer_array.append(answer_array[i:i + kraepelin_answer_rows])

            # Replace '' with None value
            for arr in new_answer_array:
                for i in range(len(arr)):
                    if arr[i] == '':
                        arr[i] = None
                    else:
                        arr[i] = int(arr[i])

            # Get skipped and not answered questions
            correct_list_count = []
            incorrect_list_count = []
            not_answered_list_count = []

            for correct, user in zip(correct_answers, new_answer_array):
                correct_count = 0
                incorrect_count = 0
                not_answered_count = 0
                for i in range(len(correct)):
                    if user[i] is None:
                        if i < len(user) - 1 and isinstance(user[i + 1], int):
                            incorrect_count += 1
                        elif i == len(user) - 1 or all(value is None for value in user[i + 1:]):
                            not_answered_count += 1
                    elif user[i] == get_last_digit(correct[i]):
                        correct_count += 1
                    else:
                        incorrect_count += 1
                correct_list_count.append(correct_count)
                incorrect_list_count.append(incorrect_count)
                not_answered_list_count.append(not_answered_count)

            # Get the Panker result
            total_correct_answer = sum(correct_list_count)
            correct_answer_each_second = total_correct_answer / kraepelin_question_columns / kraepelin_time_per_columns
            panker_percentage = correct_answer_each_second * 100

            panker_parameters = request.env['kraepelin.panker.parameter'].search([])
            for panker_parameter in panker_parameters:
                if panker_percentage >= panker_parameter.score_from - 1:
                    if panker_percentage < panker_parameter.score_to + 1:
                        kraepelin_panker_dict['score'] = panker_percentage
                        kraepelin_panker_dict['label'] = panker_parameter.name
                        kraepelin_panker_dict['description'] = panker_parameter.description
                        kraepelin_panker_dict['results'] = f"{round(correct_answer_each_second, 2)} jawaban/detik"
                        kraepelin_panker_dict['means'] = "Kecepatan Kerja"

            # Get the Tianker result
            count_answer_cols = 0
            for arr in new_answer_array:
                count_answer_cols += len(arr)

            total_wrong_and_skipped = sum(incorrect_list_count)
            total_answerable_questions = count_answer_cols
            tianker_result = (total_wrong_and_skipped / total_answerable_questions) * 100

            tianker_parameters = request.env['kraepelin.tianker.parameter'].search([])
            for tianker_parameter in tianker_parameters:
                if tianker_result >= tianker_parameter.score_from - 1:
                    if tianker_result < tianker_parameter.score_to + 1:
                        kraepelin_tianker_dict['score'] = total_wrong_and_skipped
                        kraepelin_tianker_dict['label'] = tianker_parameter.name
                        kraepelin_tianker_dict['description'] = tianker_parameter.description
                        kraepelin_tianker_dict['results'] = f"{total_wrong_and_skipped} salah/terlewatkan"
                        kraepelin_tianker_dict['means'] = "Ketelitian Kerja"

            # Get the Janker result
            max_amount_of_correct_answer = max(correct_list_count)
            min_amount_of_correct_answer = min(correct_list_count)
            ranges = max_amount_of_correct_answer - min_amount_of_correct_answer
            deviation_level = ranges / kraepelin_question_rows
            janker_result = deviation_level * 100

            janker_parameters = request.env['kraepelin.janker.parameter'].search([])
            for janker_parameter in janker_parameters:
                if janker_result >= janker_parameter.score_from - 1:
                    if janker_result < janker_parameter.score_to + 1:
                        kraepelin_janker_dict['score'] = janker_result
                        kraepelin_janker_dict['label'] = janker_parameter.name
                        kraepelin_janker_dict['description'] = janker_parameter.description
                        kraepelin_janker_dict['results'] = f"Tingkat Deviasi {round(deviation_level, 2)}%"
                        kraepelin_janker_dict['means'] = "Keajengan Kerja"

            # Get the Hanker result
            sigma_x = sum([i for i in range(1, kraepelin_question_columns + 1)])
            sigma_y = sum(correct_list_count)
            x_2 = sum([i ** 2 for i in range(1, kraepelin_question_columns + 1)])
            sigma_xy = sum([i * j for i, j in zip(list(range(1, kraepelin_question_columns + 1)), correct_list_count)])
            mean_x = 1 / kraepelin_question_columns * sigma_x
            mean_y = 1 / kraepelin_question_columns * sigma_y
            coefficient = ((kraepelin_question_columns * sigma_xy) - (sigma_x * sigma_y)) / (
                        (kraepelin_question_columns * x_2) - (sigma_x ** 2))

            base_column = 50
            generated_column = kraepelin_question_columns
            column_ranges = base_column ** 2 / generated_column ** 2

            # constant = mean_y - (coefficient * mean_x)
            constant = mean_y + (coefficient * column_ranges * mean_x)
            x0 = constant + coefficient * 0
            xn = constant + coefficient * kraepelin_question_columns
            hanker_result = xn - x0

            hanker_parameters = request.env['kraepelin.hanker.parameter'].search([])
            for hanker_parameter in hanker_parameters:
                if hanker_result >= hanker_parameter.score_from - 1 and hanker_result < hanker_parameter.score_to + 1:
                    kraepelin_hanker_dict['score'] = hanker_result
                    kraepelin_hanker_dict['label'] = hanker_parameter.name
                    kraepelin_hanker_dict['description'] = hanker_parameter.description
                    if hanker_result < 0:
                        kraepelin_hanker_dict['results'] = "Menurun"
                    else:
                        kraepelin_hanker_dict['results'] = "Meningkat"
                    kraepelin_hanker_dict['means'] = "Ketahanan Kerja"

            kraepelin_result_dict = {
                'Panker': kraepelin_panker_dict,
                'Tianker': kraepelin_tianker_dict,
                'Janker': kraepelin_janker_dict,
                'Hanker': kraepelin_hanker_dict
            }

            if survey_user_input:
                survey_user_input.kraepelin_question_array = question_array
                survey_user_input.kraepelin_answer_array = answer_array

                existing_names = survey_user_input.kraepelin_test_result_ids.mapped('name')

                for key, val in kraepelin_result_dict.items():
                    if key not in existing_names:
                        survey_user_input.kraepelin_test_result_ids = [(0, 0, {
                            'name': key,
                            'label': val['label'],
                            'score': val['score'],
                            'description': val['description'],
                            'results': val['results'],
                            'means': val['means']
                        })]

                # Generate kraepelin chart
                x_arr = [row for row in range(1, kraepelin_question_columns + 1)]
                y_arr = correct_list_count
                chart_kraepelin_result_score = False
                figure = False

                if x_arr and y_arr:
                    line_markers = go.Scatter(
                        x=x_arr,
                        y=y_arr,
                        mode='lines+markers'
                    )
                    layout = go.Layout(
                        xaxis=dict(title='x = Jumlah kolom'),
                        yaxis=dict(title='y = Jawaban benar')
                    )
                    figure = go.Figure(data=[line_markers], layout=layout)
                    chart_kraepelin_result_score = plotly.offline.plot(figure,
                                                                       include_plotlyjs=False,
                                                                       output_type='div')
                survey_user_input.chart_kraepelin_result_score = chart_kraepelin_result_score
                survey_user_input.img_chart_kraepelin_result_score = base64.b64encode(figure.to_image(
                    format='png')).decode()

    # @http.route('/token-api', type='http', auth="public", csrf=False, website=True)
    # def token_api(self,**post):
    #     cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
    #     env = request.env(user=odoo.SUPERUSER_ID)
    #     values = {}
    #     values['value'] = {}
    #     data_api = request.params

    #     print (data_api, 'data-api----')
# class Equip3HrSurveyExtend(http.Controller):
#     @http.route('/equip3_hr_survey_extend/equip3_hr_survey_extend/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_survey_extend/equip3_hr_survey_extend/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_survey_extend.listing', {
#             'root': '/equip3_hr_survey_extend/equip3_hr_survey_extend',
#             'objects': http.request.env['equip3_hr_survey_extend.equip3_hr_survey_extend'].search([]),
#         })

#     @http.route('/equip3_hr_survey_extend/equip3_hr_survey_extend/objects/<model("equip3_hr_survey_extend.equip3_hr_survey_extend"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_survey_extend.object', {
#             'object': obj
#         })

class SurveyController(SurveyController):

    @http.route('/survey/begin/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_begin(self, survey_token, answer_token, **post):
        """ Route used to start the survey user input and display the first survey page. """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state != "new":
            return {'error': _("The survey has already started.")}

        answer_sudo._mark_in_progress()

        if not answer_sudo.applicant_id:
            answer_sudo.applicant_id = post.get('applicant_id')
        if not answer_sudo.job_id:
            answer_sudo.job_id = post.get('job_position')

        return self._prepare_question_html(survey_sudo, answer_sudo, **post)