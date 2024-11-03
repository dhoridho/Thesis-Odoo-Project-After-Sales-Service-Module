
from odoo import http, _
from odoo.exceptions import UserError
from odoo.addons.web.controllers.main import Home
from odoo.http import request, route
from odoo.addons.account.controllers.portal import PortalAccount, portal_pager
from odoo.addons.survey.controllers.main import Survey
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
import base64
from collections import OrderedDict
import json
from datetime import date, datetime, timedelta
import werkzeug
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
from odoo.osv.expression import AND, OR
import datetime
import calendar

class Survey(Survey):

    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):
        res = super(Survey, self).survey_submit(survey_token, answer_token, **post)
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        answer_sudo = access_data['answer_sudo']
        if answer_sudo.state == "done" and post.get('exam_id') and post.get('exam_id') != 'false':
            # exam_id adalah exam_student_id
            exam_student_id = request.env['exam.student.line'].sudo().browse([int(post.get('exam_id'))])
            exam_id = exam_student_id.exam_id
            exam_id.sudo().write({'user_ids': [(4, request.env.user.id)]})
            answer_sudo.write({'exam_id': exam_id.id})
            # update student line ke done
            exam_student_id.sudo().button_done()
            # update exam result
            exam_result_id = request.env['exam.result'].sudo().search([('s_exam_ids', '=', exam_id.id), ('student_id', '=', exam_student_id.student_id.id)])
            exam_result_id.sudo().set_done()

        elif answer_sudo.state == "done" and post.get('assignment_id') and post.get('assignment_id') != 'false':
            answer_sudo.write({'assignment_id': post.get('assignment_id')})
            school_student_assignment_id = request.env['school.student.assignment'].browse([int(post.get('assignment_id'))])
            school_student_assignment_id.write({'state': 'done'})
            assignment_id = request.env['school.student.assignment'].sudo().search([('teacher_assignment_ids', '=', school_student_assignment_id.teacher_assignment_ids.id), ('student_id', '=', school_student_assignment_id.student_id.id)])
            assignment_id.sudo().done_assignment()
        elif answer_sudo.state == "done" and post.get('additional_id') and post.get('additional_id') != 'false':
            answer_sudo.write({'additional_id': post.get('additional_id')})
            school_additional_id = request.env['additional.exam.line'].browse([int(post.get('additional_id'))])
            school_additional_id.write({'state': 'done'})
            additional_ids = request.env['additional.exam.line'].sudo().search([('additional_exam_id', '=', school_additional_id.additional_exam_id.id), ('student_id', '=', school_additional_id.student_id.id)])
            additional_ids.sudo().done_done()

        return res

class SchoolPortal(http.Controller):
    
    @http.route(['/student/payment/validation'], type='http', auth="user", csrf=False, website=True)
    def student_payment_validation(self, **post):
        if post:
            invoice_id = int(post.get('invoice_id', False))
            payment = post.get('payment', False)
            amount = post.get('amount', False)
            date = post.get('date', False)
            receipt = post.get('receipt', False)
            remark = post.get('remark', False)
            proof_of_payment = post.get('proof_of_payment', False)
            proof_of_payment_filename = post.get('proof_of_payment_filename', False)
            invoice = request.env['account.move'].sudo().browse(invoice_id)
            invoice.write({
                'payment_details': payment,
                'amount': amount,
                'date_of_receipt': date,
                'receipt_number': receipt,
                'proof_of_payment': proof_of_payment,
                'proof_of_payment_filename': proof_of_payment_filename,
                'remarks': remark
            })
            invoice.student_payslip_id.write({
                'payment_details': payment,
                'amount': amount,
                'date_of_receipt': date,
                'receipt_number': receipt,
                'proof_of_payment': proof_of_payment,
                'proof_of_payment_filename': proof_of_payment_filename,
                'remarks': remark
            })

    def _get_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('Studentid', 'all'):
            search_domain = OR([search_domain, [('pid', 'ilike', search)]])
        if search_in in ('Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('School', 'all'):
            search_domain = OR([search_domain, [('school_id', 'ilike', search)]])
        if search_in in ('Program', 'all'):
            search_domain = OR([search_domain, [('program_id', 'ilike', search)]])
        if search_in in ('Intake', 'all'):
            search_domain = OR([search_domain, [('standard_id', 'ilike', search)]])
        if search_in in ('Status', 'all'):
            search_domain = OR([search_domain, [('state', 'ilike', search)]])
        return search_domain

    @http.route(['/sidebar'], type='http', auth='user', website=True)
    def get_sidebar_html(self):
        return request.render("equip3_school_portal.welcome_portal_template")

    @http.route(['/student/admission', '/student/admission/page/<int:page>'], type='http', auth="public", website=True)
    def student_portal_admission_list(self, sortby=None, page=1, filterby=None, groupby=None, search=None, search_in='all', **kw):
        admission = request.env['student.admission.register']
        _items_per_page = 20
        user = request.env.user
        if request.env.user.has_group('base.group_public'):
            return request.redirect('/student/admission/create')
        domain = []
        if user.has_group('base.group_portal'):
            domain += [('portal_user_id', '=', user.id)]
        elif user.has_group('base.group_user') and not user.has_group('base.group_system'):
            domain += [('student_id.user_id', '=', user.id)]
        search_sorting = {
            'none': {'label': _('All'), 'order': ''},
            'name': {'label': _('Name'), 'order': 'name'}
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        search_filter = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': [('admission_date', '=', date.today())]}
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']
        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'School' : {'input': _('School'), 'label': _('School')},
            'Program': {'input': _('Program'), 'label': _('Program')},
            'Intake': {'input': _('Intake'), 'label': _('Intake')}
        }

        if groupby is None:
            groupby = 'none'
        elif groupby == "School" and order != '':
            order = "school_id, %s" % order
        elif groupby == "Program" and order != '':
            order = "program_id, %s" % order
        elif groupby == "Intake" and order != '':
            order = "standard_id, %s" % order

        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Studentid': {'input': 'Studentid', 'label': _('Search in Student id')},
            'Name': {'input': 'Name', 'label': _('Search in Name')},
            'School': {'input': 'School', 'label': _('Search in School')},
            'Program': {'input': 'Program', 'label': _('Search in Program')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')},
            'Status': {'input': 'Status', 'label': _('Search in Status')}    
        }

        if search and search_in:
            domain += self._get_search_domain(search_in, search)

        admission_count = admission.search_count(domain)

        pager = portal_pager(
            url = "/student/admission",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total = admission_count,
            page = page,
            step = _items_per_page
        )
        admission_ids = admission.sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])

        if groupby == 'School':
            grouped_tasks = [request.env['student.student'].concat(*g) for k, g in groupbyelem(admission_ids, itemgetter('school_id'))]
        elif groupby == 'Program':
            grouped_tasks = [request.env['student.student'].concat(*g) for k, g in groupbyelem(admission_ids, itemgetter('program_id'))]
        elif groupby == 'Intake':
            grouped_tasks = [request.env['student.student'].concat(*g) for k, g in groupbyelem(admission_ids, itemgetter('standard_id'))]
        else:
            grouped_tasks = [admission_ids]

        values = {
            'admission_ids': admission_ids,
            'default_url': '/student/admission',
            'search_in': search_in,
            'search': search,
            'search_sorting': search_sorting,
            'sortby': sortby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'filterby': filterby,
            'admission_count': admission_count,
            'pager': pager,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
        }
        return request.render('equip3_school_portal.student_portal_admission_list_template', values)

    @http.route(['/student/pass/tracker', '/student/pass/tracker/page/<int:page>'], type='http', auth="user", website=True)
    def student_pass_tracker_list(self, sortby=None, page=1, filterby=None, groupby=None, search=None, search_in='all', **kw):
        _items_per_page = 20
        student_pass_tracker = request.env['student.pass.tracker']
        search_sorting = {
            'none': {'label': _('None'), 'order': ''},
            'name': {'label': _('Name'), 'order': 'name'}
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'School' : {'input': _('School'), 'label': _('School')},
            'Program': {'input': _('Program'), 'label': _('Program')},
            'Intake': {'input': _('Intake'), 'label': _('Intake')}
        }
        domain = []
        if groupby is None:
            groupby = 'none'
        elif groupby == "School" and order != '':
            order = "school_id, %s" % order
        elif groupby == "Program" and order != '':
            order = "program_id, %s" % order
        elif groupby == "Intake" and order != '':
            order = "standard_id, %s" % order
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Student ID': {'input': 'Student ID', 'label': _('Search in Student id')},
            'Student Name': {'input': 'Student Name', 'label': _('Search in Student Name')},
            'Academic Year': {'input': 'Academic Year', 'label': _('Search in Academic Year')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')}, 
        }
        user_id = request.env.user
        student_ids = []
        if user_id.has_group('base.group_system'):
            domain = []
        elif user_id.has_group('school.group_school_parent'):
            domain = []
        elif user_id.has_group('school.group_school_teacher'):
            domain = []
        elif user_id.has_group('school.group_school_student'):
            domain = [
                ('student_name', '=', user_id.related_student_id.id),
            ]
        student_pass_count = student_pass_tracker.search_count(domain)
        pager = portal_pager(
            url = "/student/pass.tracker",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total = student_pass_count,
            page = page,
            step = _items_per_page
        )
        if search and search_in:
            domain += self._get_search_domain_student_profile(search_in, search)

        student_pass = student_pass_tracker.sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        grouped_tasks = [student_pass]

        values = {
            'student_pass': student_pass,
            'sortby': sortby,
            'search_sorting': search_sorting,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'default_url': '/student/pass/tracker',
            'pager': pager,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs
        }
        return request.render("equip3_school_portal.student_pass_tracker_template", values)

    @http.route(['/course/registration'], type='http', auth="public", website=True)
    def subject_portal_admission_list(self, **post):
        if post:
            pid = post.get('pid', False)
            student_id = post.get('student_id', False)
            school_id = post.get('school_id', False)
            program_id = post.get('program_id', False)
            course_id = post.get('course_id', False)
            course_final_data = []
            if post.get('cost_data'):
                course_data = json.loads(post.get('cost_data'))
                for course in course_data:
                    course['course_id'] = int(course.get('course_id')) if course.get('course_id') != '' else False
                    course['course_code'] = course.get('course_code', False)
                    course_final_data.append((0, 0, course))
            course_dict = {
                'pid': pid,
                'student_id': student_id,
                'school_id': school_id,
                'program_id': program_id,
                'line_ids': course_final_data,
            }
            course_ids = request.env['ems.course.registration'].sudo().create(course_dict)
            course_ids.write({'state': 'applied'})
        student_id = request.env['student.student'].sudo().search([])
        school_id = request.env['school.school'].sudo().search([])
        program_id = request.env['standard.standard'].sudo().search([])
        course_id = request.env['subject.subject'].sudo().search([])
        values = {
            'student_id': student_id,
            'school_id': school_id,
            'program_id':program_id,
            'course_id': course_id,
        }
        return request.render('equip3_school_portal.course_registration_form',values)

    @http.route(['/subject/registration'], type='http', auth='public', website=True, csrf=False)
    def get_subject_registration(self, **post):
        vals = {}
        if post and post.get('course_id'):
            ems_course_id = request.env['subject.subject'].sudo().browse(int(post.get('course_id')))
            vals.update({
                'name': ems_course_id.code
            })
        return json.dumps(vals) 

    @http.route(['/student'], type='http', auth='public', website=True, csrf=False)
    def get_subject_name(self, **post):
        vals = {}
        if post and post.get('student_id'):
            student_id = request.env['student.student'].sudo().browse(int(post.get('student_id')))
            vals.update({
                'name': student_id.pid
            })
        return json.dumps(vals) 

    @http.route(['/student/admission/create'], type='http', auth="public", website=True)
    def student_portal_admission(self, student_edit_id=None, **post):
        user_id = request.env.user
        quote_msg = {}
        image = 0
        multi_users = [0]
        final_parent_data = []
        contacts = []
        ref_data = []
        family_data = []
        if post:
            student_first_name = post.get('student_first_name',False)
            student_street = post.get('student_street',False)
            student_middle_name = post.get('student_middle_name',False)
            country_id = post.get('country_id',False)
            student_last_name = post.get('student_last_name',False)
            state_id = post.get('state_id', False)
            student_zip_code = post.get('student_zip_code',False)
            student_gender = post.get('student_gender',False)
            student_phone = post.get('student_phone',False)
            student_marital_status = post.get('student_marital_status',False)
            student_mobile = post.get('student_mobile',False)
            student_email = post.get('student_email',False)
            city_name= post.get('city_name', False)
            name_persented_on_certificate = post.get('name_persented_on_certificate', False)
            pdpa_consent = post.get('pdpa_consent', False)
            nric = post.get('nric', False)
            student_type = post.get('student_type', "new_student")
            student_term = post.get('student_term', False)
            school_id = post.get('school_id', False)
            student_medium = post.get('program_id', False)
            academic_year = post.get('academic_year', False)
            standard_id = post.get('standard_id', False)
            student_name = post.get('student_name', False)
            save_as_draft = post.get('save_as_draft', False)
            date_of_birth = post.get('date_of_birth', False)
            age = post.get('age', False)
            form_mode = post.get('form_mode', False)
            existing_student_name = post.get('student_name', False)
            types = post.get('type', False)
            transfer_student = post.get('transfer_student', False)
            student_pass_registry = post.get('student_pass_registry', False)
            student_pass_status = post.get('student_pass_status', False)
            medical_check_up_date = post.get('medical_check_up_date', False)
            
            # File inputs
            files = request.httprequest.files
            personal_document_input = files.get('personal_document')
            student_pass_digital_input = files.get('student_pass_digital')
            appeal_form_input = files.get('appeal_form')
            medical_check_up_form_input = files.get('medical_check_up_form')
            medical_check_up_result_input = files.get('medical_check_up_result')

            if post.get('student_image',False):
                img = post.get('student_image')
                image = base64.b64encode(img.read())

            multi_users = request.httprequest.form.getlist('category_section_1')
            for l in range(0, len(multi_users)):
                multi_users[l] = int(multi_users[l])

            country = 'country_id' in post and post['country_id'] != '' and request.env['res.country'].browse(int(post['country_id']))
            country = country and country.exists()
            if post.get('parent_data'):
                parent_data = json.loads(post.get('parent_data'))
                for line in parent_data:
                    line['title'] = line.get('title') if line.get('title') != '' else False
                    line['state_id'] = line.get('state_id')  if line.get('state_id') != '' else False
                    line['relation_id'] = line.get('relation_id') if line.get('relation_id') != '' else False
                    line['country_id'] = line.get('country_id') if line.get('country_id') != '' else False
                    if line.get('id'):
                        parent_id = request.env['school.parent'].sudo().browse(int(line.get('id')))
                        parent_id.sudo().write(line)
                    else:
                        parent_id = request.env['school.parent'].sudo().create(line)
                    final_parent_data.append(parent_id.id)
                  
            if post.get('references_data'):
                references = json.loads(post.get('references_data'))
                for line in references:
                    if line.get('id'):
                        ref_data.append((1, line.get('id'), line))
                    else:
                        ref_data.append((0, 0, line))

            if post.get('family_data'):
                family_details = json.loads(post.get('family_data'))
                for line in family_details:
                    line['relative_name'] = line.get('name', False)
                    line['relation'] = line.get('relation') if line.get('relation') != '' else False
                    if line.get('id'):
                        family_data.append((1, line.get('id'), line))
                    else:        
                        family_data.append((0, 0, line))

            student_dict = {
                'name':student_first_name,
                'middle': student_middle_name,
                'last': student_last_name,
                'street': student_street,
                'country_id': int(country_id) if country_id else False,
                'state_id': int(state_id) if state_id else False,
                'date_of_birth': date_of_birth if date_of_birth else False,
                'age': age,
                'zip': student_zip_code,
                'gender': student_gender,
                'phone': student_phone,
                'maritual_status': student_marital_status,
                'mobile': student_mobile,
                'city': city_name,
                'email': student_email,
                'photo': image,
                'name_presented': name_persented_on_certificate,
                'parent_id': [(6, 0, final_parent_data)],
                'reference_ids': ref_data,
                'family_con_ids': family_data,
                'is_pdpa_constent': pdpa_consent,
                'nric': nric,
                'student_type': student_type,
                'school_id': int(school_id) if school_id else False,
                'program_id': int(student_medium) if student_medium else False,
                'term_id': int(student_term) if student_term else False,
                'year': int(academic_year) if academic_year else False,
                'standard_id': int(standard_id) if  standard_id else False,
                'type': types,

                # Student pass tracker informations
                'transfer_student': transfer_student,
                'student_pass_registry': student_pass_registry,
                'student_pass_status': student_pass_status,
                'med_checkup_date': medical_check_up_date if medical_check_up_date else False,
            }

            if personal_document_input:
                personal_document = base64.b64encode(personal_document_input.read())
                student_dict.update({'personal_document': personal_document})

            if student_pass_digital_input:
                student_pass_digital = base64.b64encode(student_pass_digital_input.read())
                student_dict.update({'student_pass_digital': student_pass_digital})
            
            if appeal_form_input:
                appeal_form = base64.b64encode(appeal_form_input.read())
                student_dict.update({'appeal_from': appeal_form})
            
            if medical_check_up_form_input:
                medical_check_up_form = base64.b64encode(medical_check_up_form_input.read())
                student_dict.update({'med_checkup_form': medical_check_up_form})
            
            if medical_check_up_result_input:
                medical_check_up_result = base64.b64encode(medical_check_up_result_input.read())
                student_dict.update({'med_checkup_result': medical_check_up_result})

            if user_id.has_group('base.group_portal'):
                student_dict.update({'portal_user_id': user_id.sudo().id})

            if student_name:
                if form_mode == 'create_existing':
                    student_dict['student_id'] = int(existing_student_name)
                    student_id = request.env['student.admission.register'].sudo().create(student_dict)
                    student_id.write({
                        'user_id': user_id.id,
                        'name':student_first_name,
                        'middle': student_middle_name,
                        'last': student_last_name,
                        'street': student_street,
                        'country_id': int(country_id) if country_id else False,
                        'state_id': int(state_id) if state_id else False,
                        'zip': student_zip_code,
                    })
                else:
                    student_id = request.env['student.admission.register'].sudo().browse(int(student_name))
                    if student_type == "existing_student":
                        student_name = student_id.student_id.id
                        student_dict['student_id'] = int(student_name)
                    student_id.write(student_dict)
            else:
                student_id = request.env['student.admission.register'].sudo().create(student_dict)
                student_id.write({
                    'user_id': user_id.id,
                    'name':student_first_name,
                    'middle': student_middle_name,
                    'last': student_last_name,
                    'street': student_street,
                    'country_id': int(country_id) if country_id else False,
                    'state_id': int(state_id) if state_id else False,
                    'zip': student_zip_code,
                })

            if post.get('previous_school_data'):
                previous_school_data = json.loads(post.get('previous_school_data'))
                for school_line in previous_school_data:
                    if school_line.get('id'):
                        previous_school_id = request.env['student.previous.school'].sudo().browse(int(school_line.get('id')))
                        previous_school_id.sudo().write(school_line)
                    else:
                        school_line['previous_school_id'] = student_id.id
                        request.env['student.previous.school'].sudo().create(school_line)

            if save_as_draft == 'on':
                vals = {
                    'state': 'draft'
                }
                student_id.write(vals)
                return request.redirect('/student/admission')
            else:
                student_id.action_apply()

            if student_id:
                quote_msg = {
                    'success': 'Student Admission ' + student_first_name + ' created successfully.'
                }
                return request.redirect('/student/admission/')
        title = request.env['res.partner.title'].sudo().search([])
        relations = request.env['parent.relation'].sudo().search([])
        courses = request.env['standard.standard'].sudo().search([])
        existing_student = request.env['student.student'].sudo().search([('state', '=', 'done'), ('student_type', '=', 'new_student'), ('name', '!=', False)])
        school_id = request.env['school.school'].sudo().search([])
        student_name = request.env['student.student'].sudo().search([])
        to_create_exising = False
        if user_id.has_group('school.group_school_student'):
            student_ids = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            student_name = student_ids
            if student_ids:
                to_create_exising = True
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            student_name = student_ids
        academic_year = request.env['academic.year'].sudo().search([('current', '=', True)])
        family_relation = request.env['student.relation.master'].sudo().search([])
        countries = request.env["res.country"].sudo().search([])
        lang_ids = request.env['res.lang'].sudo().search([])
        lang_data = [{'name': lang.name, 'code': lang.code} for lang in lang_ids]
        country_states = request.env["res.country"].state_ids
        parent_data = request.env['student.student'].sudo().search([('name', '=', user_id.name)])
        res_config = request.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
        attachment_id = request.env['ir.attachment'].sudo().search([('res_id', '=', res_config.id),
                ('res_model', '=', 'res.config.settings'), ('res_field', '=', 'pdpa_consent_file')], limit=1, order='id desc')
        pdpa_consent_filename = request.env['ir.config_parameter'].sudo().get_param('pdpa_consent_filename')
        if attachment_id and not attachment_id.access_token:
            attachment_id.generate_access_token()
        values = {
            'page_name': 'menu_admission_register',
            'default_url': '/student/admission/create',
            'quote_msg': quote_msg,
            'country_states': country_states,
            'countries': countries,
            'lang_data': lang_data,
            'courses': courses,
            'titles': title,
            'relations': relations,
            'existing_student':existing_student,
            'school_id': school_id,
            'academic_year': academic_year,
            'student_name': student_name,
            'family_relation':family_relation,
            'attachment_id': attachment_id and attachment_id.id or False,
            'access_token': attachment_id and attachment_id.access_token or '',
            'download': pdpa_consent_filename,
            'create_mode': True,
            'to_create_existing': to_create_exising,
            'student_email': user_id.email,
        }
        if student_edit_id:
            values.update({
                'is_edit_mode': True,
                'student_edit_id': student_edit_id,
            })
            values.pop('create_mode')
        return request.render("equip3_school_portal.student_portal_admission_template", values)
    
    @http.route(['/student/admission/create/<int:student_id>'], type='http', auth='public', methods=['GET'], website=True)
    def admission_edit_existing_student(self, student_id):
        try:
            student_id = request.env['student.admission.register'].sudo().browse(student_id)
        except:
            student_id = False
        if not student_id:
            return request.redirect('/student/admission')
        else:
            return self.student_portal_admission(student_edit_id=student_id)

    @http.route(['/student/admission/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def admission_country_infos(self, country,**kw):
        return dict(
            states=[(st.id, st.name, st.code) for st in country.state_ids],
            phone_code=country.phone_code,
            zip_required=country.zip_required,
            state_required=country.state_required,
        )

    @http.route(['/program/intake'], type='http', auth='public', website=True, csrf=False)
    def get_program_intake(self, **post):
        data = []
        if post and post.get('program_id') and post.get('academic_year'):
            academic = request.env['academic.year'].sudo().browse(int(post.get('academic_year')))
            standard_ids = request.env['school.standard'].sudo().search([('standard_id','=', int(post.get('program_id'))), ('start_year', '=', academic.code)])
            for program in standard_ids:
                val = {
                    'name': program.name,
                    'id': program.id,
                }
                data.append(val)
        return json.dumps(data)

    @http.route(['/school/program'], type='http', auth='public', website=True, csrf=False)
    def get_school_programs(self, **post):
        data = []
        if post and post.get('school_id') and post.get('school_id') != 'NaN':
            school = request.env['school.school'].sudo().browse(int(post.get('school_id')))
            for program in school.school_program_ids:
                val = {
                    'name': program.name,
                    'id': program.id,
                }
                data.append(val)
        return json.dumps(data)

    @http.route(['/existing/student/<model("student.student"):student_id>'], type='http', auth='public', website=True, csrf=False)
    def existing_student_name(self, student_id, **post):
        data = []
        reference_data = []
        previous_data = []
        family_data = []

        for parent in student_id.parent_id:
            vals = {
                'name': parent.name,
                'id': parent.id,
                'relation_id': parent.relation_id.id,
                'phone': parent.phone,
                'email': parent.email,
                'city': parent.city,
                'address': parent.street,
                'zip': parent.zip,
                'state_id': parent.state_id.id,
                'title': parent.title.id,
                'lang': parent.lang,
                'country_id': parent.country_id.id
            }
            data.append(vals)
        for reference in student_id.reference_ids:
            reference_vals = {
                'name': reference.name,
                'middle': reference.middle,
                'last': reference.last,
                'id': reference.id,
                'designation': reference.designation,
                'email': reference.email,
                'phone': reference.phone,
                'ref_gender': reference.gender
            }
            reference_data.append(reference_vals)
        for previous in student_id.previous_school_ids:
            previous_vals = {
                'name': previous.name,
                'id': previous.id,
                'registration_no': previous.registration_no,
                'admission_date': previous.admission_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'exit_date': previous.exit_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'course_id': previous.course_id.id
            }
            previous_data.append(previous_vals)
        for family in student_id.family_con_ids:
            family_vals = {
                'rel_name': family.rel_name,
                'id': family.id,
                'relative_name': family.relative_name,
                'existing_student': family.stu_name.id,
                'email': family.email,
                'relation': family.relation.id,
                'phone': family.phone
            }
            family_data.append(family_vals)
        vals = {
                'name': student_id.name or '',
                'middle': student_id.middle or '',
                'last': student_id.last or '',
                'year': student_id.year.id or '',
                'email': student_id.email or '',
                'phone': student_id.phone or '',
                'maritual_status': student_id.maritual_status or '',
                'fees_ids': student_id.fees_ids.id or '',
                'name_presented': student_id.name_presented or '',
                'nric': student_id.nric or '',
                'school_id': student_id.school_id.id or '',
                'street': student_id.street or '',
                'country_id': student_id.country_id.id or '',
                'city': student_id.city or '',
                'state_id': student_id.state_id.id or '',
                'zip': student_id.zip or '',
                'program_id': student_id.program_id.id or '',
                'standard_id': student_id.standard_id.id or '',
                'gender': student_id.gender or '',
                'date_of_birth': str(student_id.date_of_birth) or '',
                'age': student_id.age or '',
                'parent_id': data,
                'reference_id': reference_data,
                'previous_school_id': previous_data,
                'family_id': family_data,
                'type': student_id.type,
            }
        return json.dumps(vals) 
    
    @http.route(['/admission/existing/student/<model("student.admission.register"):student_id>'], type='http', auth='public', website=True, csrf=False)
    def admmission_existing_student_name(self, student_id, **post):
        data = []
        reference_data = []
        previous_data = []
        family_data = []

        for parent in student_id.parent_id:
            vals = {
                'name': parent.name,
                'id': parent.id,
                'relation_id': parent.relation_id.id,
                'phone': parent.phone,
                'email': parent.email,
                'city': parent.city,
                'address': parent.street,
                'zip': parent.zip,
                'state_id': parent.state_id.id,
                'title': parent.title.id,
                'lang': parent.lang,
                'country_id': parent.country_id.id
            }
            data.append(vals)
        for reference in student_id.reference_ids:
            reference_vals = {
                'name': reference.name,
                'middle': reference.middle,
                'last': reference.last,
                'id': reference.id,
                'designation': reference.designation,
                'email': reference.email,
                'phone': reference.phone,
                'ref_gender': reference.gender
            }
            reference_data.append(reference_vals)
        for previous in student_id.previous_school_ids:
            previous_vals = {
                'name': previous.name,
                'id': previous.id,
                'registration_no': previous.registration_no,
                'admission_date': previous.admission_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'exit_date': previous.exit_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'course_id': previous.course_id.id
            }
            previous_data.append(previous_vals)
        for family in student_id.family_con_ids:
            family_vals = {
                'rel_name': family.rel_name,
                'id': family.id,
                'relative_name': family.relative_name,
                'existing_student': family.stu_name.id,
                'email': family.email,
                'relation': family.relation.id,
                'phone': family.phone
            }
            family_data.append(family_vals)
        vals = {
                'name': student_id.name or '',
                'middle': student_id.middle or '',
                'last': student_id.last or '',
                'year': student_id.year.id or '',
                'email': student_id.email or '',
                'phone': student_id.phone or '',
                'maritual_status': student_id.maritual_status or '',
                'fees_ids': student_id.fees_ids.id or '',
                'name_presented': student_id.name_presented or '',
                'nric': student_id.nric or '',
                'school_id': student_id.school_id.id or '',
                'street': student_id.street or '',
                'country_id': student_id.country_id.id or '',
                'city': student_id.city or '',
                'state_id': student_id.state_id.id or '',
                'zip': student_id.zip or '',
                'program_id': student_id.program_id.id or '',
                'standard_id': student_id.standard_id.id or '',
                'gender': student_id.gender or '',
                'date_of_birth': str(student_id.date_of_birth) or '',
                'age': student_id.age or '',
                'parent_id': data,
                'reference_id': reference_data,
                'previous_school_id': previous_data,
                'family_id': family_data,
                'type': student_id.type,

                # Student pass tracker informations
                'personal_document': str(student_id.personal_document),
                'transfer_student': student_id.transfer_student,
                'student_pass_registry': student_id.student_pass_registry,
                'student_pass_status': student_id.student_pass_status,
                'student_pass_digital': str(student_id.student_pass_digital),
                'appeal_from': str(student_id.appeal_from),
                'med_checkup_form': str(student_id.med_checkup_form),
                'med_checkup_result': str(student_id.med_checkup_result),
                'med_checkup_date': str(student_id.med_checkup_date,)
            }
        return json.dumps(vals) 

    # @http.route(['/school/intake'], type='http', auth='public', website=True, csrf=False)
    # def get_school_program_intakes(self, **post):
    #     data = []
    #     if post:
    #         school_id = post.get('school_id', False)
    #         program_id = post.get('program_id', False)
    #         academic_year = post.get('academic_year', False)
    #         student_term = post.get('student_term', False)
    #         domain = [('school_id','=', int(school_id)),('standard_id','=', int(program_id)),('year','=', int(academic_year)),('term_id','=', int(student_term))]
    #         standard_ids = request.env['school.standard'].sudo().search(domain)
    #         for standard_id in standard_ids:
    #             vals = {
    #                 'id': standard_id.id,
    #                 'name': standard_id.name,
    #             }
    #             data.append(vals)
    #     return json.dumps(data)

    @http.route(['/student/admission/thankyou'], type='http', auth="public", website=True)
    def student_portal_thankyou(self, **post):
        return request.render("equip3_school_portal.thank_you_admission_register")

    # newly added codes
    @http.route(['/teacher/profile'], type='http', auth="user", website=True)
    def teacher_portal_profile(self, **kw):
        user_id = request.env.user
        teacher_ids = []
        if user_id.has_group('school.group_school_administration'):
            teacher_ids = request.env['school.teacher'].sudo().search([])
        else:
            teacher_ids = request.env['school.teacher'].sudo().search([('user_id', '=', request.env.user.id)])
        values = {
            'teacher_ids': teacher_ids
        }
        return request.render("equip3_school_portal.teacher_portal_profile_template", values)

    @http.route(['/teacher/profile/<model("school.teacher"):teacher_id>'], type='http', auth="user", website=True)
    def teacher_profile_list(self, teacher_id, **post):
        vals = {
            'teacher_id': teacher_id
        }
        return request.render("equip3_school_portal.teacher_profile_list_template", vals)
    
    def _get_search_domain_student_profile(self, search_in, search):
        search_domain = []
        if search_in in ('Student ID', 'all'):
            search_domain = OR([search_domain, [('student_code', 'ilike', search)]])
        if search_in in ('Student Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Academic Year', 'all'):
            search_domain = OR([search_domain, [('history_ids.academice_year_id', 'ilike', search)]])
        if search_in in ('Intake', 'all'):
            search_domain = OR([search_domain, [('history_ids.standard_id', 'ilike', search)]])
        return search_domain

    @http.route(['/student/profile', '/student/profile/page/<int:page>'], type='http', auth="user", website=True)
    def student_portal_profile(self, sortby=None, page=1, groupby=None, search=None, search_in='all', **kw):
        _items_per_page = 20
        student = request.env['student.student']
        search_sorting = {
            'none': {'label': _('None'), 'order': ''},
            'name': {'label': _('Name'), 'order': 'name'}
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'School' : {'input': _('School'), 'label': _('School')},
            'Program': {'input': _('Program'), 'label': _('Program')},
            'Intake': {'input': _('Intake'), 'label': _('Intake')}
        }
        domain = []
        if groupby is None:
            groupby = 'none'
        elif groupby == "School" and order != '':
            order = "school_id, %s" % order
        elif groupby == "Program" and order != '':
            order = "program_id, %s" % order
        elif groupby == "Intake" and order != '':
            order = "standard_id, %s" % order
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Student ID': {'input': 'Student ID', 'label': _('Search in Student id')},
            'Student Name': {'input': 'Student Name', 'label': _('Search in Student Name')},
            'Academic Year': {'input': 'Academic Year', 'label': _('Search in Academic Year')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')}, 
        }
        user_id = request.env.user
        student_ids = []
        if user_id.has_group('base.group_system'):
            domain = [('state', '=', 'done'), ('student_type', '=', 'new_student')]
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            domain = [('id', 'in', student_ids.ids)]
        elif user_id.has_group('school.group_school_teacher'):
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)], limit=1)
            student_ids = teacher_id.student_id
            domain = [('id', 'in', student_ids.ids)]
        elif user_id.has_group('school.group_school_student'):
            domain = [
                ('user_id', '=', user_id.id),
                ('state', '=', 'done'),
                ('student_type', '=', 'new_student')
            ]
        student_count = student.search_count(domain)
        pager = portal_pager(
            url = "/student/profile",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total = student_count,
            page = page,
            step = _items_per_page
        )
        if search and search_in:
            domain += self._get_search_domain_student_profile(search_in, search)
        student_ids = student.sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        if groupby == 'School':
            grouped_tasks = [student.concat(*g) for k, g in groupbyelem(student_ids, itemgetter('school_id'))]
        elif groupby == 'Program':
            grouped_tasks = [student.concat(*g) for k, g in groupbyelem(student_ids, itemgetter('program_id'))]
        elif groupby == 'Intake':
            grouped_tasks = [student.concat(*g) for k, g in groupbyelem(student_ids, itemgetter('standard_id'))]
        else:
            grouped_tasks = [student_ids]
        values = {
            'student_ids': student_ids,
            'sortby': sortby,
            'search_sorting': search_sorting,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'default_url': '/student/profile',
            'pager': pager,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs
        }
        return request.render("equip3_school_portal.student_portal_profile_template", values)

    @http.route(['/student/schedule'], type='http', auth="user", website=True)
    def student_portal_schedule(self, **kw):
        user_id = request.env.user
        schedule_ids = []
        if user_id.has_group('base.group_system'):
            schedule_ids = request.env['time.table'].sudo().search([])
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            class_ids = student_ids.mapped('standard_id')
            schedule_ids = request.env['time.table'].sudo().search([('standard_id', 'in', class_ids.ids)])
        elif user_id.has_group('school.group_school_teacher'):
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)], limit=1)
            student_ids = teacher_id.student_id
            class_ids = student_ids.mapped('standard_id')
            schedule_ids = request.env['time.table'].sudo().search([('standard_id', 'in', class_ids.ids)])
        elif user_id.has_group('school.group_school_student'):
            student_ids = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            class_ids = student_ids.standard_id
            schedule_ids = request.env['time.table'].sudo().search([('standard_id', '=', class_ids.id)])
        values = {
            'schedule_ids' : schedule_ids
        }
        return request.render("equip3_school_portal.student_schedule_template", values)
    
    def _get_search_domain_leave_request(self, search_in, search):
        search_domain = []
        if search_in in ('Type of Leave', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Intake', 'all'):
            search_domain = OR([search_domain, [('standard_id', 'ilike', search)]])
        if search_in in ('School', 'all'):
            search_domain = OR([search_domain, [('school_id', 'ilike', search)]])
        if search_in in ('Program', 'all'):
            search_domain = OR([search_domain, [('program_id', 'ilike', search)]])
        if search_in in ('Class Teacher', 'all'):
            search_domain = OR([search_domain, [('teacher_id', 'ilike', search)]])
        if search_in in ('Start Date', 'all'):
            search_domain = OR([search_domain, [('start_date', 'ilike', search)]])
        if search_in in ('End Date', 'all'):
            search_domain = OR([search_domain, [('end_date', 'ilike', search)]])
        if search_in in ('Status', 'all'):
            search_domain = OR([search_domain, [('state', 'ilike', search)]])
        return search_domain

    @http.route(['/student/leaves', '/student/leaves/page/<int:page>'], type='http', auth="user", website=True)
    def student_student_leaves(self, sortby=None, filterby=None, groupby=None, page=1, search=None, search_in='all', **kw):
        _items_per_page = 20
        search_sorting = {
            'none': {'label': _('None'), 'order': ''},
            'date': {'label': _('Start Date'), 'order': 'start_date desc'},
            'end_date': {'label': _('End Date'), 'order': 'end_date desc'},
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        user_id = request.env.user
        leave_ids = []
        if user_id.has_group('base.group_system'):
            domain = []
        elif user_id.has_group('school.group_school_parent'):
            domain = [('student_id', 'in', student_ids.ids)]
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
        elif user_id.has_group('school.group_school_teacher'):
            domain = [('student_id', 'in', student_ids.ids)]
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)], limit=1)
            student_ids = teacher_id.student_id
        elif user_id.has_group('school.group_school_student'):
            student_id = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            domain = [('student_id', '=', student_id.id)]
        today_date = date.today()
        current_week = datetime.date(today_date.year, today_date.month, today_date.day)
        start_date = current_week - timedelta(days = current_week.weekday())
        end_date = start_date + timedelta(days = 6) 

        month_start_date = today_date.replace(day=1)
        month = date.today().month
        year = date.today().year
        if month == 12:
            month_last_date = today_date.replace(year=year, month=month, day=31)
        else:
            month_last_date = today_date.replace(year=year, month=month + 1, day=1) + timedelta(days=-1)

        search_filter = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': [('start_date', '=', date.today()), ('end_date', '=', date.today())]},
            'this week': {'label': _('This Week'), 'domain': [('start_date', '>=', start_date), ('end_date', '<=', end_date)]},
            'this month': {'label': _('This Month'), 'domain': [('start_date', '>=', month_start_date), ('end_date', '<=', month_last_date)]},
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']
        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'School' : {'input': _('School'), 'label': _('School')},
            'Program': {'input': _('Program'), 'label': _('Program')},
            'Intake': {'input': _('Intake'), 'label': _('Intake')},
            'Class Teacher': {'input': _('Class Teacher'), 'label': _('Class Teacher')},  
            'Status': {'input': _('Status'), 'label': _('Status')}
        }
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Type of Leave': {'input': 'Type of Leave', 'label': _('Search in Type of Leave')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')},
            'School': {'input': 'School', 'label': _('Search in School')},
            'Program': {'input': 'Program', 'label': _('Search in Program')},
            'Class Teacher': {'input': 'Class Teacher', 'label': _('Search in Class Teacher')},
            'Start Date': {'input': 'Start Date', 'label': _('Search in Start Date')},
            'End Date': {'input': 'End Date', 'label': _('Search in End Date')}, 
            'Status': {'input': 'Status', 'label': _('Search in Status')},     
        }
        if search and search_in:
            domain += self._get_search_domain_leave_request(search_in, search)
        if groupby is None:
            groupby = 'none'
        elif groupby == "School" and order != '':
            order = "school_id, %s" % order
        elif groupby == "Program" and order != '':
            order = "program_id, %s" % order
        elif groupby == "Intake" and order != '':
            order = "standard_id, %s" % order
        elif groupby == "Class Teacher" and order != '':
            order = "teacher_id, %s" % order
        elif groupby == "Status" and order != '':
            order = "state, %s" % order
        studentleave_count = request.env['studentleave.request'].search_count(domain)
        pager = portal_pager(
            url = "/student/leaves",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total = studentleave_count,
            page = page,
            step = _items_per_page
        )
        leave_ids = request.env['studentleave.request'].sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        if groupby == 'School':
            grouped_tasks = [request.env['studentleave.request'].concat(*g) for k, g in groupbyelem(leave_ids, itemgetter('school_id'))]
        elif groupby == 'Program':
            grouped_tasks = [request.env['studentleave.request'].concat(*g) for k, g in groupbyelem(leave_ids, itemgetter('program_id'))]
        elif groupby == 'Intake':
            grouped_tasks = [request.env['studentleave.request'].concat(*g) for k, g in groupbyelem(leave_ids, itemgetter('standard_id'))]
        elif groupby == 'Class Teacher':
            grouped_tasks = [request.env['studentleave.request'].concat(*g) for k, g in groupbyelem(leave_ids, itemgetter('teacher_id'))]
        elif groupby == 'Status':
            grouped_tasks = [request.env['studentleave.request'].concat(*g) for k, g in groupbyelem(leave_ids, itemgetter('state'))]
        else:
            grouped_tasks = [leave_ids]
        values = {
            'leave_ids' : leave_ids,
            'default_url': '/student/leaves',
            'sortby': sortby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'filterby': filterby,
            'groupby': groupby,
            'search_sorting': search_sorting,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'pager': pager,
            'page_name': 'Student Leave Request',
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs
        }

        leave_id = []
        student_ids = request.env['student.student'].sudo().search([('state', '=', 'done')])
        student_data = [{
            'id': student.id,
            'name': student.name,
            "class_id": student.standard_id.name or '',
            'teacher_id': student.standard_id.user_id.name or '',
        } for student in student_ids]
        values.update({
            'leave_id': leave_id,
            "student_data": student_data,
        })
        is_student = request.env.user.has_group('school.group_school_student')
        school_setting_id = request.env.ref("equip3_school_setting.school_config_settings_data").id
        school_config = request.env["school.config.settings"].browse([school_setting_id])
        is_student_leave_request_per_subject= False
        subjects = False
        if school_config.student_leave_request_per_subject:
            is_student_leave_request_per_subject = True

        if is_student:
            student = student_ids.filtered(lambda x: x.user_id == request.env.user)
            if student:
                group_class = request.env['group.class'].sudo().search([('intake', '=', student[0].standard_id.id)], limit=1)
                if group_class:
                    subjects = group_class.subject_ids
                
                values.update({
                    'is_student': is_student,
                    'student_id': student[0].id,
                    'student_name': student[0].name,
                    'class_id': student[0].standard_id.name or '',
                    'teacher_id': student[0].standard_id.user_id.name or '',
                    'is_student_leave_request_per_subject': is_student_leave_request_per_subject,
                    'subjects': subjects,
                })
        return request.render("equip3_school_portal.student_leave_portal_list", values)

    @http.route(['/student/leave/request'], type='http', auth="user", website=True)
    def student_leave_request(self, **post):
        leave_id = []
        if post:
            type_of_leave = post.get('type_of_leave')
            student_name = int(post.get('student_id'))
            start_date = post.get('start_date')
            end_date = post.get('end_date')
            reason_for_leave = post.get('reason_for_leave')
            subject_id = post.get('subject_id')
            leave_dict = {
                'name': type_of_leave,
                'student_id': student_name,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason_for_leave,
                'is_created': True,
                'subject_id': subject_id,
            }
            leave_id = request.env['studentleave.request'].sudo().create(leave_dict)
            leave_id.onchange_student()
            leave_id._onchange_intake_pic()
            leave_id._onchange_class_pic()

            return request.redirect('/student/leaves')

        student_ids = request.env['student.student'].sudo().search([('state', '=', 'done')])
        student_data = [{
            'id': student.id,
            'name': student.name,
            "class_id": student.standard_id.name or '',
            'teacher_id': student.standard_id.user_id.name or '',
        } for student in student_ids]
        vals = {
            'leave_id': leave_id,
            "student_data": student_data,
        }
        is_student = request.env.user.has_group('school.group_school_student')
        if is_student:
            student = student_ids.filtered(lambda x: x.user_id == request.env.user)
            if student:
                vals.update({
                    'is_student': is_student,
                    'student_id': student[0].id,
                    'student_name': student[0].name,
                    'class_id': student[0].standard_id.name or '',
                    'teacher_id': student[0].standard_id.user_id.name or '',
                })
        return request.render("equip3_school_portal.student_leave_form_template",vals)

    @http.route(['/student/schedule/<model("time.table"):schedule>'], type='http', auth="user", website=True)
    def student_schedule_list(self, schedule, **post):
        vals = {
            'schedule': schedule
        }
        return request.render("equip3_school_portal.student_schedule_form_template", vals)

    def _get_search_domain_student_exam(self, search_in, search):
        search_domain = []
        if search_in in ('Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Type', 'all'):
            search_domain = OR([search_domain, [('type', 'ilike', search)]])
        if search_in in ('Student', 'all'):
            search_domain = OR([search_domain, [('exam_student_ids.student_id', 'ilike', search)]])
        if search_in in ('Subject', 'all'):
            search_domain = OR([search_domain, [('subject_id', 'ilike', search)]])
        return search_domain

    @http.route(['/student/exam', '/student/exam/page/<int:page>'], type='http', auth="user", website=True)
    def student_portal_exam(self, sortby=None, page=1, filterby=None, groupby=None, search=None, search_in='all', **kw):
        exam = request.env['exam.exam']
        _items_per_page = 20
        user_id = request.env.user
        domain = [('state','in', ['running', 'finished']), ('type', 'in', ['online', 'softcopy'])]
        if user_id.has_group('base.group_system'):
            domain += []
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            class_ids = student_ids.mapped('standard_id')
            domain += [('exam_schedule_ids.standard_id', 'in', class_ids.ids)]
        elif user_id.has_group('school.group_school_teacher'):
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)], limit=1)
            student_ids = teacher_id.student_id
            class_ids = student_ids.mapped('standard_id')
            domain += [('exam_schedule_ids.standard_id', 'in', class_ids.ids)]
        elif user_id.has_group('school.group_school_student'):
            student_id = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            domain += [('exam_student_ids.student_id', '=', student_id.id)]
            
        search_sorting = {
            'none': {'label': _('All'), 'order': ''},
            'name': {'label': _('Exam Name'), 'order': 'name'},
            'date': {'label': _('Date'), 'order': 'exam_date'}
        }
        if sortby is None:
            sortby = 'none'

        order = search_sorting[sortby]['order']

        search_filter = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': [('exam_date', '=', date.today())]}
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']

        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'Type' : {'input': _('Type'), 'label': _('Exam Type')},
            'Subject': {'input': _('Subject'), 'label': _('Subject')}
        }
        if groupby is None:
            groupby = 'none'
        elif groupby == "Type" and order != '':
            order = "type, %s" % order
        elif groupby == "Subject" and order != '':
            order = "subject_id, %s" % order

        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Name': {'input': 'Name', 'label': _('Search in Exam Name')},
            'Type': {'input': 'Type', 'label': _('Search in Exam Type')},
            'Student': {'input': 'Student', 'label': _('Search in Student')},
            'Subject': {'input': 'Subject', 'label': _('Search in Subject')} 
        }

        if search and search_in:
            domain += self._get_search_domain_student_exam(search_in, search)

        exam_count = exam.search_count(domain)

        pager = portal_pager(
            url = "/student/exam",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total = exam_count,
            page = page,
            step = _items_per_page
        )

        exam_ids = exam.sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])

        if groupby == 'Type':
            grouped_tasks = [request.env['exam.exam'].concat(*g) for k, g in groupbyelem(exam_ids, itemgetter('type'))]
        elif groupby == 'Subject':
            grouped_tasks = [request.env['exam.exam'].concat(*g) for k, g in groupbyelem(exam_ids, itemgetter('subject_id'))]
        else:
            grouped_tasks = [exam_ids]

        values = {
            'exam_ids': exam_ids,
            'exam_student_ids': exam_ids.mapped('exam_student_ids'),
            'default_url': '/student/exam',
            'search_in': search_in,
            'search': search,
            'search_sorting': search_sorting,
            'sortby': sortby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'filterby': filterby,
            'admission_count': exam_count,
            'pager': pager,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
        }
        
        return request.render("equip3_school_portal.student_exams_template", values)

    def _get_search_domain_student_additional_exam(self, search_in, search):
        search_domain = []
        if search_in in ('Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Type', 'all'):
            search_domain = OR([search_domain, [('submission_type', 'ilike', search)]])
        if search_in in ('Student', 'all'):
            search_domain = OR([search_domain, [('student_id', 'ilike', search)]])
        if search_in in ('Subject', 'all'):
            search_domain = OR([search_domain, [('subject_id', 'ilike', search)]])
        if search_in in ('Status', 'all'):
            search_domain = OR([search_domain, [('state', 'ilike', search)]])
        return search_domain
    
    @http.route(['/student/additional', '/student/additional/page/<int:page>'], type='http', auth="public", website=True)
    def student_portal_additional(self, sortby=None, page=1, filterby=None, groupby=None, search=None, search_in='all', **kw):
        additional = request.env['additional.exam.line']
        _items_per_page = 20
        user_id = request.env.user
        domain = [('state', '!=', 'draft'), ('submission_type', '!=', 'hardcopy')]
        if user_id.has_group('base.group_system'):
            domain += []
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            domain += [('student_id', 'in', student_ids.ids)]
        elif user_id.has_group('school.group_school_teacher'):
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)],limit=1)
            student_ids = teacher_id.student_id
            domain += [('student_id', 'in', student_ids.ids), ('teacher_id', '=', teacher_id.id)]
        elif user_id.has_group('school.group_school_student'):
            student_ids = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            domain += [('student_id', '=', student_ids.id)]
    
        search_sorting = {
            'none': {'label': _('All'), 'order': ''},
            'name': {'label': _('Additional Exam Name'), 'order': 'name'},
            'date': {'label': _('Date'), 'order': 'exam_date'}
        }
        if sortby is None:
            sortby = 'none'

        order = search_sorting[sortby]['order']

        search_filter = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': [('exam_date', '=', date.today())]}
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']

        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'Type' : {'input': _('Type'), 'label': _('Exam Type')},
            'Subject': {'input': _('Subject'), 'label': _('Subject')}
        }
        if groupby is None:
            groupby = 'none'
        elif groupby == "Type" and order != '':
            order = "submission_type, %s" % order
        elif groupby == "Subject" and order != '':
            order = "subject_id, %s" % order

        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Name': {'input': 'Name', 'label': _('Search in Additional Exam Name')},
            'Type': {'input': 'Type', 'label': _('Search in Exam Type')},
            'Student': {'input': 'Student', 'label': _('Search in Student')},
            'Subject': {'input': 'Subject', 'label': _('Search in Subject')},
            'Status': {'input': 'Status', 'label': _('Search in Status')} 
        }

        if search and search_in:
            domain += self._get_search_domain_student_additional_exam(search_in, search)

        additional_count = additional.search_count(domain)

        pager = portal_pager(
            url = "/student/additional",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total = additional_count,
            page = page,
            step = _items_per_page
        )

        additional_ids = additional.sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])

        if groupby == 'Type':
            grouped_tasks = [request.env['additional.exam.line'].concat(*g) for k, g in groupbyelem(additional_ids, itemgetter('submission_type'))]
        elif groupby == 'Subject':
            grouped_tasks = [request.env['additional.exam.line'].concat(*g) for k, g in groupbyelem(additional_ids, itemgetter('subject_id'))]
        else:
            grouped_tasks = [additional_ids]

        values = {
            'additional_ids': additional_ids,
            'default_url': '/student/additional',
            'search_in': search_in,
            'search': search,
            'search_sorting': search_sorting,
            'sortby': sortby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'filterby': filterby,
            'admission_count': additional_count,
            'pager': pager,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
        }
        return request.render("equip3_school_portal.student_additional_exams_template", values)

    @http.route(['/student/additional/<model("additional.exam.line"):additional_id>'], type='http', auth="public",
                website=True)
    def additional_exam_portal(self, additional_id, **kw):
        attachment_id = request.env['ir.attachment'].sudo().search(
            [('res_id', '=', additional_id.id), ('res_model', '=', 'additional.exam.line')], order="id desc",
            limit=1)
        if attachment_id and additional_id.attached_homework_file_name and attachment_id.name != additional_id.attached_homework_file_name:
            attachment_id.sudo().write({'name': additional_id.attached_homework_file_name})
        vals = {
            'additional_id': additional_id,
            'attachment_id': attachment_id,
            'submission_type': additional_id.submission_type and additional_id.submission_type.capitalize() or "",
        }
        return request.render("equip3_school_portal.additional_exam_portal_form", vals)

    def _get_search_domain_student_assignment(self, search_in, search):
        search_domain = []
        if search_in in ('Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Type', 'all'):
            search_domain = OR([search_domain, [('submission_type', 'ilike', search)]])
        if search_in in ('Teacher', 'all'):
            search_domain = OR([search_domain, [('teacher_id', 'ilike', search)]])
        if search_in in ('Student', 'all'):
            search_domain = OR([search_domain, [('student_id', 'ilike', search)]])
        if search_in in ('Subject', 'all'):
            search_domain = OR([search_domain, [('subject_id', 'ilike', search)]])
        if search_in in ('Intake', 'all'):
            search_domain = OR([search_domain, [('standard_id', 'ilike', search)]])
        if search_in in ('Status', 'all'):
            search_domain = OR([search_domain, [('state', 'ilike', search)]])
        return search_domain
    
    @http.route(['/student/assignment', '/student/assignment/page/<int:page>'], type='http', auth="public", website=True)
    def student_portal_assignment(self, sortby=None, page=1, filterby=None, groupby=None, search=None, search_in='all', **kw):
        assignment = request.env['school.student.assignment']
        _items_per_page = 20
        user_id = request.env.user
        domain = [('state','!=','draft'), ('submission_type', '!=', 'hardcopy')]
        if user_id.has_group('base.group_system'):
            domain += []
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            domain += [('student_id', 'in', student_ids.ids)]
        elif user_id.has_group('school.group_school_teacher'):
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)], limit=1)
            student_ids = teacher_id.student_id
            domain += [('student_id', 'in', student_ids.ids), ('teacher_id', '=', teacher_id.id)]
        elif user_id.has_group('school.group_school_student'):
            student_ids = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            domain += [('student_id', '=', student_ids.id)]
            
        search_sorting = {
            'none': {'label': _('All'), 'order': ''},
            'assign_date': {'label': _('Assign Date'), 'order': 'assign_date'},
            'due_date': {'label': _('Due Date'), 'order': 'due_date'}
        }
        if sortby is None:
            sortby = 'none'

        order = search_sorting[sortby]['order']

        search_filter = {
            'all': {'label': _('All'), 'domain': []},
            'today_assign_date': {'label': _('Today (Assign Date)'), 'domain': [('assign_date', '=', date.today())]},
            'today_due_date': {'label': _('Today (Due Date)'), 'domain': [('due_date', '=', date.today())]}
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']

        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'Type' : {'input': _('Type'), 'label': _('Submission Type')},
            'Subject': {'input': _('Subject'), 'label': _('Subject')},
            'Intake': {'input': _('Intake'), 'label': _('Intake')}
        }
        if groupby is None:
            groupby = 'none'
        elif groupby == "Type" and order != '':
            order = "submission_type, %s" % order
        elif groupby == "Subject" and order != '':
            order = "subject_id, %s" % order
        elif groupby == "Intake" and order != '':
            order = "standard_id, %s" % order

        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Name': {'input': 'Name', 'label': _('Search in Assignment Name')},
            'Type': {'input': 'Type', 'label': _('Search in Submission Type')},
            'Teacher': {'input': 'Teacher', 'label': _('Search in Teacher')},
            'Student': {'input': 'Student', 'label': _('Search in Student')},
            'Subject': {'input': 'Subject', 'label': _('Search in Subject')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')},
            'Status': {'input': 'Status', 'label': _('Search in Status')} 
        }

        if search and search_in:
            domain += self._get_search_domain_student_assignment(search_in, search)

        assignment_count = assignment.search_count(domain)

        pager = portal_pager(
            url = "/student/assignment",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total = assignment_count,
            page = page,
            step = _items_per_page
        )

        assignment_ids = assignment.sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        
        if groupby == 'Type':
            grouped_tasks = [request.env['school.student.assignment'].concat(*g) for k, g in groupbyelem(assignment_ids, itemgetter('submission_type'))]
        elif groupby == 'Subject':
            grouped_tasks = [request.env['school.student.assignment'].concat(*g) for k, g in groupbyelem(assignment_ids, itemgetter('subject_id'))]
        elif groupby == 'Intake':
            grouped_tasks = [request.env['school.student.assignment'].concat(*g) for k, g in groupbyelem(assignment_ids, itemgetter('standard_id'))]
        else:
            grouped_tasks = [assignment_ids]

        values = {
            'assignment_ids': assignment_ids,
            'default_url': '/student/assignment',
            'search_in': search_in,
            'search': search,
            'search_sorting': search_sorting,
            'sortby': sortby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'filterby': filterby,
            'admission_count': assignment_count,
            'pager': pager,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
        }
        return request.render("equip3_school_portal.student_assignment_template", values)

    @http.route(['/student/assignment/<model("school.student.assignment"):assignment_id>'], type='http', auth="public", website=True)
    def student_assignment_portal(self, assignment_id, **kw):
        attachment_id = request.env['ir.attachment'].sudo().search([('res_id', '=', assignment_id.id), ('res_model', '=', 'school.student.assignment')], order="id desc", limit=1)
        if attachment_id and assignment_id.attached_homework_file_name and attachment_id.name != assignment_id.attached_homework_file_name:
            attachment_id.sudo().write({'name': assignment_id.attached_homework_file_name})
        vals = {
            'assignment_id': assignment_id,
            'attachment_id': attachment_id,
            'submission_type': assignment_id.submission_type and assignment_id.submission_type.capitalize() or "",
        }
        return request.render("equip3_school_portal.student_assignment_portal_form", vals)
    
    @http.route(['/student/profile/edit/<model("student.student"):student_id>'], type='http', auth="user", website=True)
    def student_profile_list_editable(self, student_id, **post):
        student_id = student_id.sudo()
        certificate_ids = student_id.certificate_ids
        certificate_data = []
        for certi in certificate_ids:
            attachment_id = request.env['ir.attachment'].sudo().search([
                ('res_id', '=', certi.id), 
                ('res_field', '=', 'certi'), 
                ('res_model', '=', 'student.certificate')
                ], order="id desc", limit=1)
            if attachment_id and certi.file_name != attachment_id.name:
                attachment_id.sudo().write({'name': certi.file_name})
            certificate_data.append({
                'description':   certi.description,
                'attachment_id': attachment_id,
            })
        mother_tongue = request.env['mother.toungue'].sudo().search([])
        cast = request.env['student.cast'].sudo().search([])
        countries = request.env['res.country'].sudo().search([])
        relations = request.env['parent.relation'].sudo().search([])
        family_relation = request.env['student.relation.master'].sudo().search([])
        existing_student = request.env['student.student'].sudo().search([('state', '=', 'done'), ('student_type', '=', 'new_student')])
        vals = {
            'existing_student': existing_student,
            'certificate_ids': certificate_data,
            'student_id': student_id,
            'mother_tongue': mother_tongue,
            'existing_mother_tongue': student_id.mother_tongue.id,
            'cast': cast,
            'existing_cast': student_id.cast_id.id,
            'maritual': student_id.maritual_status,
            'gender': student_id.gender,
            'countries': countries,
            'relations': relations,
            'family_relation': family_relation,
        }
        return request.render("equip3_school_portal.student_profile_list_editable_template", vals)

    @http.route(['/student/profile/save/<model("student.student"):student_id>'], type='http', auth="user", website=True)
    def student_profile_list_save(self, student_id, **post):
        final_parent_data = []
        family_data = []
        vals = {
            'name': post.get('name'),
            'email': post.get('email'),
            'mobile': post.get('mobile'),
            'street': post.get('address'),
            'cast_id': post.get('cast'),
            'date_of_birth': post.get('birthday'),
            'gender': post.get('gender'),
            'mother_tongue': post.get('mother_tongue'),
            'maritual_status': post.get('maritual')            
        }
        if post.get('parent_data'):
            parent_data = json.loads(post.get('parent_data'))
            for line in parent_data:
                line['relation_id'] = line.get('relation_id') if line.get('relation_id') != '' else False
                line['country_id'] = line.get('country_id') if line.get('country_id') != '' else False
                if line.get('id'):
                    parent_id = request.env['school.parent'].sudo().browse(int(line.get('id')))
                    parent_id.sudo().write(line)
                else:
                    parent_id = request.env['school.parent'].sudo().create(line)
                final_parent_data.append(parent_id.id)
        if post.get('family_data'):
            family_details = json.loads(post.get('family_data'))
            for line in family_details:
                line['relative_name'] = line.get('name', False)
                line['relation'] = line.get('relation') if line.get('relation') != '' else False
                if line.get('id'):
                    family_data.append((1, line.get('id'), line))
                else:        
                    family_data.append((0, 0, line))
        vals.update({
            'parent_id': [(6, 0, final_parent_data)],
            'family_con_ids': family_data,
        })
        student_id.sudo().write(vals)
        return request.redirect('/student/profile/%d'%(student_id.id))

    @http.route(['/student/profile/<model("student.student"):student_id>'], type='http', auth="user", website=True)
    def student_profile_list(self, student_id, **post):
        current_student = request.env['student.student'].sudo().browse(int(student_id))
        current_user = request.env.user

        if current_student.user_id.id != current_user.id or current_student.student_type != 'new_student':
            return request.render('equip3_school_portal.403_permission_denied')

        certificate_ids = student_id.certificate_ids
        certificate_data = []
        for certi in certificate_ids:
            attachment_id = request.env['ir.attachment'].sudo().search([('res_id', '=', certi.id), ('res_field', '=', 'certi'), ('res_model', '=', 'student.certificate')], order="id desc", limit=1)
            if attachment_id and certi.file_name != attachment_id.name:
                attachment_id.sudo().write({'name': certi.file_name})
            certificate_data.append({
                'description':   certi.description,
                'attachment_id': attachment_id,
            })
        vals = {
            'certificate_ids': certificate_data,
            'student_id': student_id
        }
        return request.render("equip3_school_portal.student_profile_list_template", vals)

    @http.route(['/student/assignment/submit/<model("school.student.assignment"):assignment>'], type='http', auth="public", website=True)
    def student_assignment_submit_portal(self, assignment, **post):
        assignment_dict = {'state': 'done'}
        if post:
            submit_assign = base64.b64encode(post.get('submit_assignment').read())
            file = post.get('file', False)
            assignment_dict.update({
                'submit_assign': submit_assign,
                'file_name': file,
            })
        assignment.sudo().write(assignment_dict)
        return request.redirect('/student/assignment')

    @http.route(['/student/additional/submit/<model("additional.exam.line"):additional>'], type='http',
                auth="public", website=True)
    def additional_exam_submit_portal(self, additional, **post):
        additional_dict = {'state': 'done'}
        if post:
            submit_assign = base64.b64encode(post.get('submit_additional').read())
            file = post.get('file', False)
            additional_dict.update({
                'submit_assign': submit_assign,
                'file_name': file,
            })
        additional.sudo().write(additional_dict)
        return request.redirect('/student/additional')
    
    def _get_search_domain_regular_class(self, search_in, search):
        search_domain = []
        if search_in in ('Date', 'all'):
            search_domain = OR([search_domain, [('class_date', 'ilike', search)]])
        if search_in in ('Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Program', 'all'):
            search_domain = OR([search_domain, [('program_id', 'ilike', search)]])
        if search_in in ('Intake', 'all'):
            search_domain = OR([search_domain, [('intake_id', 'ilike', search)]])
        if search_in in ('Teacher', 'all'):
            search_domain = OR([search_domain, [('teacher_id', 'ilike', search)]])
        if search_in in ('Study Day', 'all'):
            search_domain = OR([search_domain, [('study_day', 'ilike', search)]])
        if search_in in ('Classroom', 'all'):
            search_domain = OR([search_domain, [('classroom_id', 'ilike', search)]])
        if search_in in ('Term', 'all'):
            search_domain = OR([search_domain, [('term_id', 'ilike', search)]])
        if search_in in ('Subject', 'all'):
            search_domain = OR([search_domain, [('subject_id', 'ilike', search)]])
        if search_in in ('Start Time', 'all'):
            search_domain = OR([search_domain, [('start_time', 'ilike', search)]])
        if search_in in ('End Time', 'all'):
            search_domain = OR([search_domain, [('end_time', 'ilike', search)]])
        return search_domain

    @http.route(['/regular/class', '/regular/class/page/<int:page>'], type='http', auth='user', website=True)
    def regular_class_schedule(self, sortby=None, filterby=None, groupby=None, page=1, search=None, search_in='all', **kw):
        user_id = request.env.user
        _items_per_page = 20
        if user_id.has_group('school.group_school_teacher'):
            related_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)],limit=1)
            domain = [('teacher_id', '=', related_id.id)]
        elif user_id.has_group('school.group_school_parent'):
            related_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)],limit=1)
            related_id = related_id.student_id
            related_id = request.env['ems.classes.line'].sudo().search([('student_id', 'in', related_id.ids)])
            domain = [('id', 'in', related_id.mapped('ems_classes_id').ids)]
        elif user_id.has_group('school.group_school_student'):
            related_id = request.env['student.student'].search([('user_id', '=', user_id.id)], limit=1)
            related_id = request.env['ems.classes.line'].sudo().search([('student_id', 'in', related_id.ids)])
            domain = [('id', 'in', related_id.mapped('ems_classes_id').ids)]
        else:
            regular_class = request.env['ems.classes'].sudo().search([])
            domain = [('id', 'in', regular_class.ids)]
        search_sorting = {
            'none': {'label': _('None'), 'order': ''},
            'date': {'label': _('Date'), 'order': 'class_date desc'}
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Date': {'input': 'Date', 'label': _('Search in Date')},
            'Name': {'input': 'Name', 'label': _('Search in Name')},
            'Program': {'input': 'Program', 'label': _('Search in Program')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')},
            'Teacher': {'input': 'Teacher', 'label': _('Search in Teacher')},
            'Study Day': {'input': 'Study Day', 'label': _('Search in Study Day')},
            'Classroom': {'input': 'Classroom', 'label': _('Search in Classroom')},
            'Term': {'input': 'Term', 'label': _('Search in Term')},
            'Subject': {'input': 'Subject', 'label': _('Search in Subject')},
            'Start Time': {'input': 'Start Time', 'label': _('Search in Start Time')},
            'End Time': {'input': 'End Time', 'label': _('Search in End Time')}
        }
        if search and search_in:
            domain += self._get_search_domain_regular_class(search_in, search)
        today_date = date.today()
        current_week = datetime.date(today_date.year, today_date.month, today_date.day)
        start_date = current_week - timedelta(days = current_week.weekday())
        end_date = start_date + timedelta(days = 6)
        search_filter = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today Class'), 'domain': [('class_date', '=', date.today())]},
            'this': {'label': _('This Week Class'), 'domain': [('class_date', '>=', start_date), ('class_date', '<=', end_date)]}   
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']
        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'Intake' : {'input': _('Intake'), 'label': _('Intake')},
            'Teacher': {'input': _('Teacher'), 'label': _('Teacher')},
            'Study Day': {'input': _('Study Day'), 'label': _('Study Day')},
            'Subject': {'input': _('Subject'), 'label': _('Subject')},
            'Classes Type': {'input': _('Classes Type'), 'label': _('Classes Type')},
        }
        if groupby is None:
            groupby = 'none'
        elif groupby == "Intake" and order != '':
            order = "intake_id, %s" % order
        elif groupby == "Teacher" and order != '':
            order = "teacher_id, %s" % order
        elif groupby == "Study Day" and order != '':
            order = "study_day, %s" % order
        elif groupby == "Subject" and order != '':
            order = "subject_id, %s" % order
        elif groupby == "Classes Type" and order != '':
            order = "classes_type, %s" % order
        class_count = request.env['ems.classes'].search_count(domain)
        pager = portal_pager(
            url = "/regular/class",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total = class_count,
            page = page,
            step = _items_per_page
        )
        regular_class_ids = request.env['ems.classes'].sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        if groupby == 'Intake':
            grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in groupbyelem(regular_class_ids, itemgetter('intake_id'))]
        elif groupby == 'Teacher':
            grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in groupbyelem(regular_class_ids, itemgetter('teacher_id'))]
        elif groupby == 'Study Day':
            grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in groupbyelem(regular_class_ids, itemgetter('study_day'))]
        elif groupby == 'Subject':
            grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in groupbyelem(regular_class_ids, itemgetter('subject_id'))]
        elif groupby == 'Classes Type':
            grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in groupbyelem(regular_class_ids, itemgetter('classes_type'))]
        else:
            grouped_tasks = [regular_class_ids]
        values = {
            'regular_class_ids': regular_class_ids,
            'default_url': '/regular/class',
            'sortby': sortby,
            'search_sorting': search_sorting,
            'filterby': filterby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'groupby': groupby,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks,
            'pager': pager,
            'page_name': 'Classes',
            'search_in': search_in,
            'search': search,
            'searchbar_inputs': searchbar_inputs
        }
        return request.render('equip3_school_portal.regular_class', values)

    def get_domain_class_schedule(self):
        user_id = request.env.user
        if user_id.has_group('school.group_school_teacher'):
            related_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)],
                                                                     limit=1)
            domain = [('teacher_id', '=', related_id.id)]
        elif user_id.has_group('school.group_school_parent'):
            related_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)],
                                                                    limit=1)
            related_id = related_id.student_id
            related_id = request.env['ems.classes.line'].sudo().search([('student_id', 'in', related_id.ids)])
            domain = [('id', 'in', related_id.mapped('ems_classes_id').ids)]
        elif user_id.has_group('school.group_school_student'):
            related_id = request.env['student.student'].search([('user_id', '=', user_id.id)], limit=1)
            intake_ids = request.env['school.standard'].sudo().search([('intake_student_line_ids.student_id', '=', related_id.id)])
            domain = [('intake_id', 'in', intake_ids.ids)]
        else:
            domain = []
        return domain

    @http.route(['/regular/class/calendar'], type='http', auth='user', website=True)
    def regular_class_schedule_calendar(self, sortby=None, filterby=None, groupby=None, page=1, search=None, search_in='all',
                               **kw):
        domain = self.get_domain_class_schedule()
        start_date = date.today().replace(day=1)
        next_date = start_date.replace(day=28) + timedelta(days=4)
        next_month_date = (next_date - timedelta(days=next_date.day)) + timedelta(days=1)

        domain += [
                ('class_date', '>=', datetime.datetime.strptime(start_date.strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT).strftime("%Y-%m-%d 00:00:00")),
                ('class_date', '<', datetime.datetime.strptime(next_month_date.strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT).strftime("%Y-%m-%d 00:00:00")),
        ]
        regular_class_ids = request.env['ems.classes'].sudo().search(domain)
        data = self._get_class_data(regular_class_ids)
        values = {
            'regular_class_ids': regular_class_ids,
            'data': data
        }
        return request.render('equip3_school_portal.regular_class_calendar', values)

    def _get_class_data(self, regular_class_ids):
        data = []
        for regular_class in regular_class_ids:
            title = ""
            if regular_class.start_time and regular_class.end_time:
                start_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(regular_class.start_time * 60, 60))
                end_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(regular_class.end_time * 60, 60))
                title += '(' + str(start_time) + ' - ' + str(end_time) + ')'
            if regular_class.subject_id:
                title += ' - ' + regular_class.subject_id.code + ' - ' + regular_class.subject_id.name
            if regular_class.teacher_id:
                title += ' - ' + regular_class.teacher_id.name
            vals = {
                'id': regular_class.id,
                'title': title,
                'start': regular_class.class_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
            }
            data.append(vals)
        return data

    # @http.route(['/exam/class'], type='http', auth='user', website=True)
    # def exam_class_schedule(self, sortby=None, filterby=None, groupby=None, page=1, search=None, search_in='all', **kw):
    #     user_id = request.env.user
    #     _items_per_page = 20
    #     if user_id.has_group('school.group_school_teacher'):
    #         related_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)],limit=1)
    #         domain = [('teacher_id', '=', related_id.id)]
    #     elif user_id.has_group('school.group_school_parent'):
    #         related_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
    #         related_id = related_id.student_id
    #         related_id = request.env['ems.classes.line'].sudo().search([('student_id', 'in', related_id.ids)])
    #         domain = [('id', 'in', related_id.mapped('ems_classes_id').ids)]

    #     elif user_id.has_group('school.group_school_student'):
    #         related_id = request.env['student.student'].search([('user_id', '=', user_id.id)], limit=1)
    #         related_id = request.env['ems.classes.line'].sudo().search([('student_id', '=', related_id.id)])
    #         domain = [('id', 'in', related_id.mapped('ems_classes_id').ids), ('classes_type', '=', 'exam')]
    #     else:
    #         regular_class = request.env['ems.classes'].sudo().search([('classes_type', '=', 'exam')])
    #         domain = [('id', 'in', regular_class.ids)]
    #     search_sorting = {
    #         'none': {'label': _('None'), 'order': ''},
    #         'date': {'label': _('Date'), 'order': 'class_date desc'}
    #     }
    #     if sortby is None:
    #         sortby = 'none'
    #     order = search_sorting[sortby]['order']
    #     searchbar_inputs = {
    #         'all': {'input': 'all', 'label': _('Search in All')},
    #         'Date': {'input': 'Date', 'label': _('Search in Date')},
    #         'Name': {'input': 'Name', 'label': _('Search in Name')},
    #         'Program': {'input': 'Program', 'label': _('Search in Program')},
    #         'Intake': {'input': 'Intake', 'label': _('Search in Intake')},
    #         'Teacher': {'input': 'Teacher', 'label': _('Search in Teacher')},
    #         'Study Day': {'input': 'Study Day', 'label': _('Search in Study Day')},
    #         'Classroom': {'input': 'Classroom', 'label': _('Search in Classroom')},
    #         'Term': {'input': 'Term', 'label': _('Search in Term')},
    #         'Subject': {'input': 'Subject', 'label': _('Search in Subject')},
    #         'Start Time': {'input': 'Start Time', 'label': _('Search in Start Time')},
    #         'End Time': {'input': 'End Time', 'label': _('Search in End Time')}
    #     }
    #     if search and search_in:
    #         domain += self._get_search_domain_regular_class(search_in, search)
    #     today_date = date.today()
    #     current_week = datetime.date(today_date.year, today_date.month, today_date.day)
    #     start_date = current_week - timedelta(days=current_week.weekday())
    #     end_date = start_date + timedelta(days=6)
    #     search_filter = {
    #         'all': {'label': _('All'), 'domain': []},
    #         'today': {'label': _('Today Class'), 'domain': [('class_date', '=', date.today())]},
    #         'this': {'label': _('This Week Class'),
    #                  'domain': [('class_date', '>=', start_date), ('class_date', '<=', end_date)]}
    #     }
    #     if filterby is None:
    #         filterby = 'all'
    #     domain += search_filter[filterby]['domain']
    #     search_group = {
    #         'none': {'input': 'none', 'label': _('None')},
    #         'Intake': {'input': _('Intake'), 'label': _('Intake')},
    #         'Teacher': {'input': _('Teacher'), 'label': _('Teacher')},
    #         'Study Day': {'input': _('Study Day'), 'label': _('Study Day')},
    #         'Subject': {'input': _('Subject'), 'label': _('Subject')},
    #     }
    #     if groupby is None:
    #         groupby = 'none'
    #     elif groupby == "Intake" and order != '':
    #         order = "intake_id, %s" % order
    #     elif groupby == "Teacher" and order != '':
    #         order = "teacher_id, %s" % order
    #     elif groupby == "Study Day" and order != '':
    #         order = "study_day, %s" % order
    #     elif groupby == "Subject" and order != '':
    #         order = "subject_id, %s" % order
    #     class_count = request.env['ems.classes'].search_count(domain)
    #     pager = portal_pager(
    #         url="/exam/class",
    #         url_args={'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby,
    #                   'groupby': groupby},
    #         total=class_count,
    #         page=page,
    #         step=_items_per_page
    #     )
    #     exam_class_ids = request.env['ems.classes'].sudo().search(domain, order=order, limit=_items_per_page,
    #                                                           offset=pager['offset'])
    #     if groupby == 'Intake':
    #         grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in
    #                          groupbyelem(exam_class_ids, itemgetter('intake_id'))]
    #     elif groupby == 'Teacher':
    #         grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in
    #                          groupbyelem(exam_class_ids, itemgetter('teacher_id'))]
    #     elif groupby == 'Study Day':
    #         grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in
    #                          groupbyelem(exam_class_ids, itemgetter('study_day'))]
    #     elif groupby == 'Subject':
    #         grouped_tasks = [request.env['ems.classes'].concat(*g) for k, g in
    #                          groupbyelem(exam_class_ids, itemgetter('subject_id'))]
    #     else:
    #         grouped_tasks = [exam_class_ids]
    #     values = {
    #         'exam_class_ids': exam_class_ids,
    #         'default_url': '/exam/class',
    #         'sortby': sortby,
    #         'search_sorting': search_sorting,
    #         'filterby': filterby,
    #         'search_filter': OrderedDict(sorted(search_filter.items())),
    #         'groupby': groupby,
    #         'search_group': search_group,
    #         'grouped_tasks': grouped_tasks,
    #         'pager': pager,
    #         'page_name': 'Exam Classes',
    #         'search_in': search_in,
    #         'search': search,
    #         'searchbar_inputs': searchbar_inputs
    #     }
    #     return request.render('equip3_school_portal.class_portal_exam_list', values)
    
    def _get_search_domain_attendance(self, search_in, search):
        search_domain = []
        if search_in in ('Date', 'all'):
            search_domain = OR([search_domain, [('date', 'ilike', search)]])
        if search_in in ('Name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('Program', 'all'):
            search_domain = OR([search_domain, [('program_id', 'ilike', search)]])
        if search_in in ('Intake', 'all'):
            search_domain = OR([search_domain, [('standard_id', 'ilike', search)]])
        if search_in in ('Academic Year', 'all'):
            search_domain = OR([search_domain, [('year_id', 'ilike', search)]])
        if search_in in ('Term', 'all'):
            search_domain = OR([search_domain, [('term_id', 'ilike', search)]])
        if search_in in ('Subject', 'all'):
            search_domain = OR([search_domain, [('subject_id', 'ilike', search)]])
        if search_in in ('Teacher', 'all'):
            search_domain = OR([search_domain, [('teacher_id', 'ilike', search)]])
        if search_in in ('Status', 'all'):
            search_domain = OR([search_domain, [('state', 'ilike', search)]])
        return search_domain

    # @http.route(['/student/attendance/<int:attendance_id>'], type='http', auth='user', website=True, method=['GET', 'POST'])
    # def get_daily_attendance(self, attendance_id=None):
    #     if attendance_id:
    #         attendance_id = request.env['daily.attendance'].browse(attendance_id)
    #         if request.httprequest.method == 'POST':
    #             if request.env.user.has_group('school.group_school_administration'):
    #                 attendance_id.sudo().attendance_validate()
    #                 return request.redirect('/student/attendance')
    #             elif request.env.user.has_group('school.group_school_teacher'):
    #                 if attendance_id.user_id != request.env.user:
    #                     return request.render('website.page_404')
    #                 else:
    #                     attendance_id.sudo().attendance_validate()
    #                     return request.redirect("/student/attendance")
    #         values = {
    #             'attendance_id': attendance_id,
    #         }
    #         return request.render('equip3_school_portal.daily_attendance_form', values)

    @http.route(['/student/attendance', '/student/attendance/page/<int:page>'], type='http', auth='user', website=True)
    def student_attendance_list(self, groupby=None, sortby=None, search=None, search_in='all', filterby=None, page=1, **kw):
        domain = []
        _items_per_page = 20
        search_sorting = {
            'none': {'label': _('None'), 'order': ''},
            'date': {'label': _('Date'), 'order': 'date desc'}
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        search_filter = {
            'all' : {'label' : _('All'), 'domain': []},
            'today' : {'label' : _('Today Attendance'), 'domain': [('date', '=', date.today())]}
        }
        if filterby is None:
            filterby = 'all'
        domain += search_filter[filterby]['domain']
        search_group = {
                'none': {'input': 'none', 'label': _('None')},
                'Program': {'input': _('Program'), 'label': _('Program')},
                'Intake': {'input': _('Intake'), 'label': _('Intake')},
                'Academic Year': {'input': _('Academic Year'), 'label': _('Academic Year')},
                'Term': {'input': _('Term'), 'label': _('Term')},
                'Teacher': {'input': _('Teacher'), 'label': _('Teacher')},
                'Subject': {'input': _('Subject'), 'label': _('Subject')}
            }
        if groupby is None:
            groupby = 'none'
        elif groupby == "Program" and order != '':
            order = "program_id, %s" % order
        elif groupby == "Intake" and order != '':
            order = "standard_id, %s" % order
        elif groupby == "academic year" and order != '':
            order = "year_id, %s" % order
        elif groupby == "Term" and order != '':
            order = "term_id, %s" % order
        elif groupby == "Teacher" and order != '':
            order = "teacher_id, %s" % order
        elif groupby == "Subject" and order != '':
            order = "subject_id, %s" % order
        if search and search_in:
            domain += self._get_search_domain_attendance(search_in, search)
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Date': {'input': 'Studentid', 'label': _('Search in Student id')},
            'Name': {'input': 'Name', 'label': _('Search in Name')},
            'Program': {'input': 'Program', 'label': _('Search in Program')},
            'Intake': {'input': 'Intake', 'label': _('Search in Intake')},
            'Academic Year': {'input': 'Academic Year', 'label': _('Search in Academic Year')},
            'Term': {'input': 'Term', 'label': _('Search in Term')},
            'Subject': {'input': 'Subject', 'label': _('Search in Subject')},
            'Teacher': {'input': 'Teacher', 'label': _('Search in Teacher')},
            'Status': {'input': 'Status', 'label': _('Search in Status')}    
        }
        if request.env.user.has_group('school.group_school_teacher'):
            employee_id = request.env['hr.employee'].search([('user_id', '=', request.env.user.id)], limit=1)
            teacher_id = request.env['school.teacher'].search([('employee_id', '=', employee_id.id)], limit=1)
            domain += [('user_id', '=', teacher_id.id)]
        attendance_count = request.env['daily.attendance'].search_count(domain)
        pager = portal_pager(
            url = "/student/attendance",
            url_args = {'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby, 'groupby': groupby},
            total=attendance_count,
            page=page,
            step=_items_per_page
        )
        attendance_id = request.env['daily.attendance'].search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        if groupby == 'Program':
            grouped_tasks = [request.env['daily.attendance'].concat(*g) for k, g in groupbyelem(attendance_id, itemgetter('program_id'))]
        elif groupby == 'Intake':
            grouped_tasks = [request.env['daily.attendance'].concat(*g) for k, g in groupbyelem(attendance_id, itemgetter('standard_id'))]
        elif groupby == 'academic year':
            grouped_tasks = [request.env['daily.attendance'].concat(*g) for k, g in groupbyelem(attendance_id, itemgetter('year_id'))]
        elif groupby == 'Term':
            grouped_tasks = [request.env['daily.attendance'].concat(*g) for k, g in groupbyelem(attendance_id, itemgetter('term_id'))]
        elif groupby == 'Teacher':
            grouped_tasks = [request.env['daily.attendance'].concat(*g) for k, g in groupbyelem(attendance_id, itemgetter('teacher_id'))]
        elif groupby == 'Subject':
            grouped_tasks = [request.env['daily.attendance'].concat(*g) for k, g in groupbyelem(attendance_id, itemgetter('subject_id'))]
        else:
            grouped_tasks = [attendance_id]
        values = {
            'attendance_ids': attendance_id,
            'sortby': sortby,
            'search_sorting': search_sorting,
            'default_url': '/student/attendance',
            'filterby': filterby,
            'search_filter': OrderedDict(sorted(search_filter.items())),
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs,
            'groupby': groupby,
            'pager': pager,
            'search_group': search_group,
            'grouped_tasks': grouped_tasks
        }
        return request.render('equip3_school_portal.daily_attendance_list', values)

    def _get_search_domain_academic_tracking(self, search_in, search):
        search_domain = []
        if search_in in ('Student', 'all'):
            search_domain = OR([search_domain, [('student_id', 'ilike', search)]])
        if search_in in ('School', 'all'):
            search_domain = OR([search_domain, [('school_id', 'ilike', search)]])
        if search_in in ('Program', 'all'):
            search_domain = OR([search_domain, [('program_id', 'ilike', search)]])
        return search_domain
    
    @http.route(['/student/academic/tracking/<int:academic_tracking_id>'], type='http', auth='user', website=True, method=['GET'])
    def get_academic_tracking_record(self, academic_tracking_id=None):
        current_user = request.env.user
        current_student = current_user.related_student_id
        academic_tracking = current_student.academic_tracking_ids.filtered(lambda at: at.id == academic_tracking_id)
        if not academic_tracking:
            return request.render('equip3_school_portal.403_permission_denied')

        if academic_tracking_id:
            academic_tracking_id = request.env['academic.tracking'].browse(academic_tracking_id)
            values = {
                'academic_tracking_id': academic_tracking_id.sudo(),
                'default_url': '/student/academic/tracking',
            }
            return request.render('equip3_school_portal.academic_tracking_form', values)

    @http.route(['/student/academic/tracking', '/student/academic/tracking/page/<int:page>'], type='http', auth='user', website=True, method=['GET'])
    def get_academic_tracking(self, groupby=None, sortby=None, search=None, search_in='all', page=1, **kw):
        _items_per_page = 20
        search_sorting = {
            'none': {'label': _('None'), 'order': ''}
        }
        if sortby is None:
            sortby = 'none'
        order = search_sorting[sortby]['order']
        search_group = {
            'none': {'input': 'none', 'label': _('None')},
            'Student': {'input': _('Student'), 'label': _('Student')},
            'School' : {'input': _('School'), 'label': _('School')},
            'Program': {'input': _('Program'), 'label': _('Program')}, 
        }
        if groupby is None:
            groupby = 'none'
        elif groupby == "Student" and order != '':
            order = "student_id, %s" % order
        elif groupby == "School" and order != '':
            order = "school_id, %s" % order
        elif groupby == "Program" and order != '':
            order = "program_id, %s" % order

        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'Student': {'input': 'Student', 'label': _('Search in Student')},
            'Program': {'input': 'Program', 'label': _('Search in Program')},
            'School': {'input': 'School', 'label': _('Search in School')},
        }

        user_id = request.env.user
        if user_id.has_group('school.group_school_student'):
            domain = [('student_id', '=', user_id.name)]
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            domain = [('student_id', 'in', student_ids.ids)]
        else:
            domain = []
        if search and search_in:
            domain += self._get_search_domain_academic_tracking(search_in, search)

        academic_tracking_count = request.env['academic.tracking'].sudo().search_count(domain)
        pager = portal_pager(
            url = "/student/academic/tracking",
            url_args = {'search_in': search_in, 'search': search, 'groupby': groupby},
            total=academic_tracking_count,
            page=page,
            step=_items_per_page
        )
        academic_tracking_ids = request.env['academic.tracking'].sudo().search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        if groupby == 'Student':
            grouped_tasks = [request.env['academic.tracking'].concat(*g) for k, g in groupbyelem(academic_tracking_ids, itemgetter('student_id'))]
        elif groupby == 'School':
            grouped_tasks = [request.env['academic.tracking'].concat(*g) for k, g in groupbyelem(academic_tracking_ids, itemgetter('school_id'))]
        elif groupby == 'Program':
            grouped_tasks = [request.env['academic.tracking'].concat(*g) for k, g in groupbyelem(academic_tracking_ids, itemgetter('program_id'))]
        else:
            grouped_tasks = [academic_tracking_ids]
        values = {
            'academic_tracking_ids': academic_tracking_ids,
            'default_url': '/student/academic/tracking',
            'grouped_tasks': grouped_tasks,
            'groupby': groupby,
            'search_group': search_group,
            'sortby': sortby,
            'pager': pager,
            'search_sorting': search_sorting,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs
        }
        return request.render('equip3_school_portal.academic_tracking_list', values)

class Home(Home):
    
    @http.route("/web/login", type="http", auth="public", website=True)
    def web_login(self, redirect=None, **kw):
        """
        This method will redirect user to the portal or internal system.
        If user login as parent/student/portal, it will be redirected to portal.
        If user login as internal user, it will redirected to the internal system.
        """
        response = super(Home, self).web_login(redirect=redirect, **kw)
        if request.httprequest.method == "POST":
            uid = request.env.user
            if uid:
                if (
                    uid.has_group("school.group_school_parent")
                    or uid.has_group("school.group_school_student")
                    or uid.has_group("base.group_portal")
                ):
                    return request.redirect("/")
                return request.redirect("/web")
            return response
        return response

    @http.route("/web", type="http", auth="public", website=True)
    def web_client(self, s_action=None, **kw):
        """
        Prevent Parents/Students/Portal users from accessing the /web route.
        """
        uid = request.env.user
        if uid and (
            uid.has_group("school.group_school_parent")
            or uid.has_group("school.group_school_student")
            or uid.has_group("base.group_portal")
        ):
            return request.redirect("/")
        return super(Home, self).web_client(s_action, **kw)

class PortalAccount(PortalAccount):
    
    
    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        res = super(PortalAccount, self).portal_my_invoice_detail(invoice_id, access_token=access_token,
                                                                  report_type=report_type, download=download, **kw)
        attachment_id = request.env['ir.attachment'].search(
            [('res_model', '=', 'res.config.settings'), ('res_field', '=', 'payment_instruction')], limit=1,
            order="id desc")
        if attachment_id and not attachment_id.access_token:
            attachment_id.generate_access_token()
        res.qcontext['payment_instruction'] = attachment_id and attachment_id.id or False
        res.qcontext['payment_instruction_token'] = attachment_id and attachment_id.access_token or False
        return res

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = super(PortalAccount, self).portal_my_invoices(page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, filterby=filterby, **kw)
        user_id = request.env.user
        domain = []
        if user_id.has_group('base.group_system'):
            domain = [('student_payslip_id', '!=', False)]
        elif user_id.has_group('school.group_school_parent'):
            parent_id = request.env['school.parent'].sudo().search([('partner_id', '=', user_id.partner_id.id)], limit=1)
            student_ids = parent_id.student_id
            domain = [('student_payslip_id.student_id', 'in', student_ids.ids)]
        elif user_id.has_group('school.group_school_teacher'):
            teacher_id = request.env['school.teacher'].sudo().search([('employee_id.user_id', '=', user_id.id)], limit=1)
            student_ids = teacher_id.student_id
            domain = [('student_payslip_id.student_id', 'in', student_ids.ids)]
        elif user_id.has_group('school.group_school_student'):
            student_ids = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            domain = [('student_payslip_id.student_id', '=', student_ids.id)]
        elif user_id.has_group('base.group_portal'):
            student_ids = request.env['student.student'].sudo().search([('user_id', '=', user_id.id)], limit=1)
            domain = [('student_payslip_id.student_id', '=', student_ids.id)]
        elif user_id.has_group('school.group_school_administration'):
            domain = [('state', '!=', 'draft')]

        invoice_count = request.env['account.move'].sudo().search_count(domain)
        pager = portal_pager(
            url="/my/invoices",
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        invoice_ids = request.env['account.move'].sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])

        values.qcontext.update({
            'invoices': invoice_ids,
            'pager': pager,
        })
        return values
