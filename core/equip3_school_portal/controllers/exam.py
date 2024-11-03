from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request, route

import base64

class ExamController(http.Controller):
    @http.route(['/exam/<model("exam.student.line"):exam_student_id>'], type='http', auth='user', website=True)
    def exam_portal(self, exam_student_id, **kw):
        vals = {'exam_id': exam_student_id.exam_id, 'student_id': exam_student_id.student_id}

        if exam_student_id.sudo().exam_id.type == 'softcopy':
            vals.update({'result_id': self.get_exam_result_id(exam_student_id.exam_id, exam_student_id.student_id)})
        elif exam_student_id.sudo().exam_id.type == 'online':
            vals.update({'survey_name': exam_student_id.exam_id.sudo().question_id.display_name})

        return request.render('equip3_school_portal.exam_form_template', vals)
    
    @http.route(['/exam/submit/<model("exam.exam"):exam_id>'], type='http', auth='user', website=True, method=['POST'])
    def exam_submission(self, exam_id, **post):
        if post and post.get('submit_exam') and post.get('exam_result_id'):
            file = post.get('submit_exam')
            exam_result_id = request.env['exam.result'].sudo().browse(int(post.get('exam_result_id')))
            exam_student_line_id = request.env['exam.student.line'].sudo().search([('exam_id', '=', exam_id.id), ('student_id', '=', exam_result_id.student_id.id)], limit=1)
            # update exam result submission file
            exam_result_id.write({
                'exam_submission': base64.b64encode(file.read()), 
                'submission_file_name': file.filename,
                'state': 'done',
                })

            # update exam_id student line
            exam_student_line_id.button_done()

            # remove from user_ids
            exam_id.sudo().write({'user_ids': [(4, request.env.user.id)]})

            return request.redirect('/student/exam')
        else:
            raise UserError('Error on posting') 

    # @http.route(['/student/assignment/<model("school.student.assignment"):assignment_id>'], type='http', auth="user", website=True)
    # def student_assignment_portal(self, assignment_id, **kw):
    #     attachment_id = request.env['ir.attachment'].sudo().search([('res_id', '=', assignment_id.id), ('res_model', '=', 'school.student.assignment')], order="id desc", limit=1)
    #     if attachment_id and assignment_id.attached_homework_file_name and attachment_id.name != assignment_id.attached_homework_file_name:
    #         attachment_id.sudo().write({'name': assignment_id.attached_homework_file_name})
    #     vals = {
    #         'assignment_id': assignment_id,
    #         'attachment_id': attachment_id,
    #         'submission_type': assignment_id.submission_type and assignment_id.submission_type.capitalize() or "",
    #     }
    #     return request.render("equip3_school_portal.student_assignment_portal_form", vals)

    def get_exam_result_id(self, exam_id, student_id=False): 
        if not student_id:
            return request.env['exam.result'].search([('s_exam_ids', '=', exam_id.id), ('student_id', '=', self.get_student_id().id)])
        else:
            return request.env['exam.result'].search([('s_exam_ids', '=', exam_id.id), ('student_id', '=', student_id.id)])

    def get_student_id(self):
        return request.env['student.student'].search([('user_id', '=', request.env.user.id)], limit=1)

    def get_attachment_id(self, exam_id):
        return request.env['ir.attachment'].sudo().search([('res_id', '=', exam_id.id), ('res_model', '=', 'exam.exam')], order='id desc', limit=1)