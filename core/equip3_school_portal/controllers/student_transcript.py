from odoo import http, _
from odoo.http import request, route

import json

class StudentTranscript(http.Controller):
    @http.route(['/student/transcript'], type='http', auth='user', website=True)
    def student_transcript(self, **post):
        if post:
            term_ids = request.httprequest.form.getlist('term_ids');
            academic_id = request.env['academic.tracking'].sudo().search([
                ('student_id', '=', int(post['student_id'])),
                ('program_id', '=', int(post['program_id'])),
            ], limit=1);
            values = {
                'student': academic_id.id,
                'program': int(post['program_id']),
                'intake': int(post['intake_id']),
                'print_all': True if 'print_all' in post else False,
                'academic_year': int(post['academic_year_id']) if 'academic_year_id' in post else False,
                'term': [(6,0,term_ids)],
            }
            wizard_id = request.env['academic.tracking.transcript'].sudo().create(values)
            redirect_str = '/report/pdf/equip3_school_report.wizard_student_transcript_tmp_web/%d'%(wizard_id.id)
            return request.redirect(redirect_str)
        else:
            user_id = request.env.user
            student_domain = []
            if user_id.has_group('school.group_school_parent'):
                parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
                child_ids = parent_id.student_id
                student_domain = [('id', 'in', child_ids.ids)]
            elif user_id.has_group('school.group_school_student'):
                student_domain = [('user_id', '=', user_id.id)]

            student_ids = request.env['student.student'].sudo().search(student_domain)
            academic_ids = request.env['academic.year'].sudo().search([])
            if len(student_ids) == 1:
                academic_id = request.env['academic.tracking'].sudo().search([
                    ('student_id', '=', student_ids.id),
                    ('program_id', '=', student_ids.sudo().program_id.id),
                ], limit=1);
                values = {
                    'student_ids': student_ids,
                    'program_ids': student_ids.sudo().program_id,
                    'intake_ids': academic_id.sudo().all_score_subject_ids.intake_id,
                    'academic_year_ids': academic_ids,
                }
            else:
                values = {
                    'student_ids': student_ids,
                    'academic_year_ids': academic_ids,
                }

            return request.render('equip3_school_portal.student_transcript_template', values)
    
    @http.route('/student/transcript/get_program', type='http', auth='user', website=True)
    def get_program_ids(self, **get):
        data = []
        if get['student_id']:
            student_ids = request.env['student.student'].sudo().browse(int(get['student_id']))
            program_ids = student_ids.sudo().program_id
            for program_id in program_ids:
                data.append({'id': program_id.id, 'name': program_id.name})
        return json.dumps(data)

    @http.route('/student/transcript/get_intake', type='http', auth='user', website=True)
    def get_intake_ids(self, **get):
        data = []
        if get['student_id'] and get['program_id']:
            academic_id = request.env['academic.tracking'].sudo().search([
                ('student_id', '=', int(get['student_id'])),
                ('program_id', '=', int(get['program_id']))])
            intake_ids = academic_id.sudo().intake_ids.intake_id
            for intake_id in intake_ids:
                data.append({'id': intake_id.id, 'name': intake_id.name})
        return json.dumps(data)

    @http.route(['/student/transcript/get_term'], type='http', auth='user', website=True)
    def get_term_ids(self, **get):
        data=[]
        if get['academic_year']:
            year_id = request.env['academic.year'].sudo().browse(int(get['academic_year']))
            month_ids = request.env['academic.month'].sudo().search([('year_id', '=', int(get['academic_year']))])
            for month in month_ids:
                data.append({'id':month.id,'name': month.name})
        return json.dumps(data);