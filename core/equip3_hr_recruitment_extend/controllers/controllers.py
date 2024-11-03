# -*- coding: utf-8 -*-
from datetime import timedelta, date
import datetime
from distutils.command import check
import werkzeug
from dateutil.relativedelta import relativedelta
import odoo
from odoo import http, fields
from odoo.exceptions import UserError
from odoo.http import content_disposition, Controller, request, route
import json
from odoo.addons.survey.controllers.main import Survey
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.addons.survey.controllers.survey_session_manage import UserInputSession
import base64
import os
from odoo.exceptions import UserError, ValidationError
import pytz
import io
import fitz  
import pytesseract
import re
from PIL import Image


class WebsiteHrRecruitment(WebsiteHrRecruitment):

    def sitemap_jobs(env, rule, qs):
        if not qs or qs.lower() in '/jobs':
            yield {'loc': '/jobs'}


    @http.route('/get-skill-type', type='json', auth='public')
    def get_skill_type(self):
        skill_type_obj = request.env['hr.skill.type']
        result = []
        skill_types = skill_type_obj.sudo().search([]).read(['name'])
        return skill_types


    @http.route('/get-skill-other-list', type='json', auth='public')
    def get_skill_other_list(self,skill_type_id):
        skill_type_obj = request.env['hr.skill.type']
        result = {}
        skill_types = skill_type_obj.sudo().browse(skill_type_id)
        result['skill'] = skill_types.skill_ids.read(['name'])
        result['level'] = skill_types.skill_level_ids.read(['name'])
        return result

    @http.route([
        '/jobs',
        '/jobs/country/<model("res.country"):country>',
        '/jobs/department/<model("hr.department"):department>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>',
        '/jobs/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/office/<int:office_id>',
        '/jobs/department/<model("hr.department"):department>/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>/office/<int:office_id>',
    ], type='http', auth="public", website=True, sitemap=sitemap_jobs)

    def jobs(self, country=None, department=None, office_id=None, **kwargs):
        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))

        Country = env['res.country']
        Jobs = env['hr.job']
        dep_obj = env['hr.department']
        company_obj = env['res.company']
        partner_obj = env['res.partner']
        companies = company_obj.sudo().search([])
        offices = []
        work_locations = env['work.location.object'].sudo().search([])
        office_arr = partner_obj
        for c in companies:
            if c.partner_id not in office_arr and c.partner_id.city and c.partner_id.country_id:
                office_arr+=c.partner_id
        if office_arr:
            offices = office_arr

        # List jobs available to current UID
        domain = request.website.website_domain()
        domain+=[('website_published','=',True)]
        if kwargs.get('jobname'):
            domain+=[('name','ilike',kwargs['jobname'])]
        job_ids = Jobs.search(domain, order="is_published desc, no_of_recruitment desc").ids
        # Browse jobs as superuser, because address is restricted
        jobs = Jobs.sudo().browse(job_ids)

        # Default search by user country
        if not (country or department or office_id or kwargs.get('all_countries')):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                countries_ = Country.search([('code', '=', country_code)])
                country = countries_[0] if countries_ else None
                if not any(j for j in jobs if j.address_id and j.address_id.country_id == country):
                    country = False

        # Filter job / office for country
   

        # Deduce departments and countries offices of those jobs
        departments = set(j.department_id for j in jobs if j.department_id)
        countries = set(o.country_id for o in offices if o.country_id)

        if department:
            jobs = [j for j in jobs if j.department_id and j.department_id.id == department.id]
        if office_id:
            jobs = [j for j in jobs if j.custom_work_location_id and j.custom_work_location_id.id == office_id]
        else:
            office_id = False

        # Render page
        return request.render("website_hr_recruitment.index", {
            'jobs': jobs,
            'countries': countries,
            'departments': dep_obj.sudo().search([]),
            'offices': offices,
            'country_id': country,
            'department_id': department,
            'office_id': office_id,
            'work_locations':work_locations,
        })

class Recruiter(http.Controller):
    def get_ocr_png(self,base64_png):
            png_bytes = base64.b64decode(base64_png)
            png_pil = Image.open(io.BytesIO(png_bytes))
            all_names = []
            all_emails = []
            all_id = []
            text = pytesseract.image_to_string(png_pil, lang="eng")
            pattern_name = r'(Name:|Nama Lengkap:|Name :) (.+)'
            pattern_email = r'[\w\.-]+@[\w\.-]+'
            pattern_id = r'\b\d{16}\b'   
            name_match = re.search(pattern_name, text, re.IGNORECASE)
            if name_match:
                all_names.append(name_match.group(2))
            
            email_match = re.findall(pattern_email, text, re.IGNORECASE)
            if email_match:
                all_emails.extend(email_match)
                
            id_match = re.findall(pattern_id, text, re.IGNORECASE)
            if id_match:
                all_id.extend(id_match)
                
            return all_names[0] if all_names else False,all_emails[0] if all_emails else False ,all_id[0] if all_id else False
    
    
    def get_ocr(self,base64_pdf):
        pdf_bytes = base64.b64decode(base64_pdf.decode("utf-8"))
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        all_names = []
        all_emails = []
        all_id = []
        text = ""
        pattern_name = r'(Name:|Nama Lengkap:|Name :) (.+)'
        pattern_email = r'[\w\.-]+@[\w\.-]+'
        pattern_id = r'\b\d{16}\b'
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            images = page.get_images(full=True)
            text += page.get_text()
            if images:            
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_data = base_image["image"]
                    try:
                        img_pixmap = fitz.Pixmap(image_data)
                        img_pil = Image.frombytes("RGB", [img_pixmap.width, img_pixmap.height], img_pixmap.samples)
                        
                        extracted_text = pytesseract.image_to_string(img_pil, lang="eng")
                    except ValueError:
                        pass
                    name_match = re.search(pattern_name, extracted_text, re.IGNORECASE)
                   
                    if name_match:
                        all_names.append(name_match.group(1))                
                    email_match = re.findall(pattern_email, extracted_text, re.IGNORECASE)
                    if email_match:
                        all_emails.extend(email_match)        
                    id_match = re.findall(pattern_id, extracted_text, re.IGNORECASE)
                    if id_match:
                        all_id.extend(id_match)
                    
                    img_pixmap = None  
            else:
                name_match = re.search(pattern_name, text, re.IGNORECASE)
                if name_match:
                    all_names.append(name_match.group(2))
                email_match = re.findall(pattern_email, text, re.IGNORECASE)
                if email_match:
                    all_emails.extend(email_match)
                    
                id_match = re.findall(pattern_id, text, re.IGNORECASE)
                if id_match:
                    all_id.extend(id_match)
                
        pdf_document.close()
        return all_names[0] if all_names else False,all_emails[0] if all_emails else False ,all_id[0] if all_id else False


    @http.route(['/interview/invite/schedule/cancel'], type='http', auth="public", website=True, sitemap=True)
    def interview_invite_schedule_cancel(self, **kwargs):
        app_obj = request.env['hr.applicant'].sudo()
        hi_obj = request.env['applicant.schedulling.meeting.result.history'].sudo()
        calendar_obj = request.env['applicant.schedulling.meeting.result.confirmed'].sudo()
        calendar_event_obj = request.env['calendar.event'].sudo()
        res = {}
        applicant_id = int(kwargs.get('applicant_id'))
        meeting_ids = request.env['applicant.schedulling.meeting.result'].sudo().search([],order='id desc').sudo().filtered(lambda line:  applicant_id in line.sudo().applicant_ids.ids)
        if meeting_ids:
            app = app_obj.browse(applicant_id)
            title_mail = (app.stage_replace_id.display_name or '-') +' : '+ (app.job_id.display_name or '-')
            meeting_datetime = ''
            meeting_datetime1 = ''
            meeting_datetime = datetime.datetime.strftime(meeting_ids[0].date, '%A, %B %d,%Y')
            if meeting_ids[0].from_time:
                meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].from_time * 60, 60))
            meeting_datetime1+= " - "
            if meeting_ids[0].to_time:
                meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].to_time * 60, 60))
                if meeting_ids[0].to_time >= 12:
                    meeting_datetime1+=' PM'
                else:
                    meeting_datetime1+=' AM'
            hi_obj.create({
                'meeting_result_id':meeting_ids[0].id,
                'name':title_mail,
                'applicant_id':applicant_id,
                'when':meeting_datetime+'\n'+meeting_datetime1,
                'location':'N/A',
                'status':'Canceled',
                'reasons':kwargs.get('reason_cancel'),
            })
            # meeting_ids[0].write({'applicant_ids':[(2,applicant_id)]})
            if meeting_ids[0].line_ids:
                confirmed = meeting_ids[0].line_ids.filtered(lambda line:  applicant_id == line.applicant_id.id)
                if confirmed:
                    confirmed.unlink()
            calendar  = calendar_event_obj.search([('applicant_name','=',kwargs['name'])])
            if calendar:
                calendar.unlink()
            res = {
            'title':title_mail,

            'meeting':meeting_ids[0],
            'meeting_datetime':meeting_datetime,
            'meeting_datetime1':meeting_datetime1,
            'name':kwargs['name'],
            'email_from':kwargs['email'],
            'name1':meeting_ids[0].interviewer.name,
            'email_from1':meeting_ids[0].interviewer.email,

            }
        return request.render("equip3_hr_recruitment_extend.interview_invite_cancel", res)

    @http.route(['/interview/invite/schedule'], type='http', auth="public", website=True, sitemap=True)
    def interview_invite_schedule(self, **kwargs):
        app_obj = request.env['hr.applicant'].sudo()
        calendar_obj = request.env['applicant.schedulling.meeting.result.confirmed'].sudo()
        hi_obj = request.env['applicant.schedulling.meeting.result.history'].sudo()
        res = {}
        res['reschedule'] = kwargs.get('reschedule')
        pic_arr = []
        meeting_datetime = ''
        title_mail = ''
        meeting_datetime1 = ''

        app = app_obj.browse(int(kwargs['applicant_id']))
        title_mail = (app.stage_replace_id.display_name or '-') +' : '+ (app.job_id.display_name or '-')

        meeting_ids = request.env['applicant.schedulling.meeting.result'].sudo().search([],order='id desc').sudo().filtered(lambda line:  int(kwargs.get('applicant_id')) in line.sudo().applicant_ids.ids)
        if meeting_ids and not kwargs.get('reschedule'):
            if meeting_ids[0].date:
                meeting_datetime = datetime.datetime.strftime(meeting_ids[0].date, '%A, %B %d,%Y')
                if meeting_ids[0].from_time:
                    meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].from_time * 60, 60))
                meeting_datetime1+= " - "
                if meeting_ids[0].to_time:
                    meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].to_time * 60, 60))
                    if meeting_ids[0].to_time >= 12:
                        meeting_datetime1+=' PM'
                    else:
                        meeting_datetime1+=' AM'

            if kwargs.get('applicant_id'):
                app = app_obj.browse(int(kwargs['applicant_id']))
                
            reschedule_url = '/interview/invite/schedule?name='+(kwargs['name'] or '')+'&email='+(kwargs['email'] or '')+'&phone='+kwargs['phone']+'&reschedule=1&applicant_id='+kwargs.get('applicant_id')
            data_app = {
            'title':title_mail,
            'meeting':meeting_ids[0],
            'meeting_datetime':meeting_datetime,
            'meeting_datetime1':meeting_datetime1,
            'name':kwargs['name'],
            'applicant_id':int(kwargs.get('applicant_id')),
            'email_from':kwargs['email'],
            'name1':meeting_ids[0].interviewer.name,
            'email_from1':meeting_ids[0].interviewer.email,
            'reschedule_url': reschedule_url

            }
            return request.render("equip3_hr_recruitment_extend.interview_invite_reschedule", data_app)

        if kwargs.get('applicant_id'):
            
            app = app_obj.browse(int(kwargs['applicant_id']))
        
            for u in app.stage_replace_id.user_ids:
                if u.id not in pic_arr:
                    pic_arr.append(u.id)
        res['pic_arr'] = pic_arr
        if kwargs.get('calendar_id'):
            

            calendar_result_obj = request.env['applicant.schedulling.meeting.result'].sudo().search([('id','=',kwargs['calendar_id'])])
            calendar_result_obj.is_applicant_shadow = True
            timehour = float(kwargs['time'].split(':')[0])
            timehour1 = kwargs['time'].split(':')[1]
            timehour_minutes =  float(timehour1.split()[0])/60
            timehour+=timehour_minutes

            app.sudo().write({
                'name':kwargs['name'],
                'email_from':kwargs['email'],
                'partner_mobile':kwargs['phone']
            })
            calendar_obj.create({
                'applicant_id':int(kwargs['applicant_id']),
                # 'date':kwargs['date'],
                'time':timehour,
                'parent_id':int(kwargs['calendar_id']),
                
            })

            attendees = []
            if calendar_result_obj.interviewer.partner_id:
                attendees.append(calendar_result_obj.interviewer.partner_id.id)

            user_tz = request.env.user.partner_id.tz or 'UTC'
            local = pytz.timezone(user_tz)
            
            interview_date = calendar_result_obj.date
            start_hours, start_minutes = divmod(abs(calendar_result_obj.from_time) * 60, 60)
            start_minutes = round(start_minutes)
            if start_minutes == 60:
                start_minutes = 0
                start_hours += 1
                
            interview_start_time = datetime.time(int(start_hours), int(start_minutes))
            interview_start_datetime = datetime.datetime.combine(interview_date, interview_start_time)
            interview_date_start = local.localize(interview_start_datetime).astimezone(pytz.UTC).replace(tzinfo=None)

            end_hours, end_minutes = divmod(abs(calendar_result_obj.to_time) * 60, 60)
            end_minutes = round(end_minutes)
            if end_minutes == 60:
                end_minutes = 0
                end_hours += 1

            interview_end_time = datetime.time(int(end_hours), int(end_minutes))
            interview_end_datetime = datetime.datetime.combine(interview_date, interview_end_time)
            interview_date_end = local.localize(interview_end_datetime).astimezone(pytz.UTC).replace(tzinfo=None)

            duration = int(calendar_result_obj.to_time - calendar_result_obj.from_time)

            calendar_event_obj = request.env['calendar.event'].sudo()
            calendar_tags = request.env['calendar.event.type'].sudo().search([('name','=','Interview')],limit=1)
            tags_list = []
            if calendar_tags:
                tags_list.append(calendar_tags.id)
            
            
            
            if not kwargs.get('reschedule'):
                print('aaaaaa')
            else:
                calendar  = calendar_event_obj.search([('applicant_name','=',kwargs['name'])])
                if calendar:
                    calendar.unlink()


            calendar_event = calendar_event_obj.create({
                'name': title_mail,
                'partner_ids': [(6,0, attendees)],
                'start': interview_date_start,
                'stop': interview_date_end,
                'duration': duration,
                'categ_ids': [(6,0, tags_list)],
                'user_id': calendar_result_obj.interviewer.id,
                'applicant_name': kwargs['name'],
                'location':'N/A',
            })
            calendar_result_obj.calendar_event_id = calendar_event.id

            if meeting_ids and kwargs.get('reschedule'):
                title_mail = (app.stage_replace_id.display_name or '-') +' : '+ (app.job_id.display_name or '-')
                meeting_datetime = ''
                meeting_datetime1 = ''
                if meeting_ids[0].date:
                    meeting_datetime = datetime.datetime.strftime(meeting_ids[0].date, '%A, %B %d,%Y')
                    if meeting_ids[0].from_time:
                        meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].from_time * 60, 60))
                    meeting_datetime1+= " - "
                    if meeting_ids[0].to_time:
                        meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].to_time * 60, 60))
                        if meeting_ids[0].to_time >= 12:
                            meeting_datetime1+=' PM'
                        else:
                            meeting_datetime1+=' AM'
                hi_obj.create({
                    'meeting_result_id':meeting_ids[0].id,
                    'name':title_mail,
                    'applicant_id':app.id,
                    'when':meeting_datetime+'\n'+meeting_datetime1,
                    'location':'N/A',
                    'status':'Reschedule',
                })

                # meeting_ids[0].write({'applicant_ids':[(2,app.id)]})
                if meeting_ids[0].line_ids:
                    confirmed = meeting_ids[0].line_ids.filtered(lambda line:  app.id == line.applicant_id.id)
                    if confirmed:
       
                        confirmed.unlink()

            meeting_ids = request.env['applicant.schedulling.meeting.result'].sudo().browse(int(kwargs['calendar_id']))
            if meeting_ids[0].date:
                meeting_datetime1 = ''
                meeting_datetime = datetime.datetime.strftime(meeting_ids[0].date, '%A, %B %d,%Y')
                if meeting_ids[0].from_time:
                    meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].from_time * 60, 60))
                meeting_datetime1+= " - "
                if meeting_ids[0].to_time:
                    meeting_datetime1+= '{0:02.0f}:{1:02.0f}'.format(*divmod(meeting_ids[0].to_time * 60, 60))
                    if meeting_ids[0].to_time >= 12:
                        meeting_datetime1+=' PM'
                    else:
                        meeting_datetime1+=' AM'

            title_mail = (app.stage_replace_id.display_name or '-') +' : '+ (app.job_id.display_name or '-')
            reschedule_url = '/interview/invite/schedule?name='+(kwargs['name'] or '')+'&email='+(kwargs['email'] or '')+'&phone='+kwargs['phone']+'&reschedule=1&applicant_id='+kwargs.get('applicant_id')
            hi_obj.create({
                    'meeting_result_id':int(kwargs['calendar_id']),
                    'name':title_mail,
                    'applicant_id':app.id,
                    'when':meeting_datetime+'\n'+meeting_datetime1,
                    'location':'N/A',
                    'status':'Scheduled',
                })

            data_app = {
            'title':title_mail,
            'meeting':meeting_ids[0],
            'meeting_datetime':meeting_datetime,
            'meeting_datetime1':meeting_datetime1,
            'name':kwargs['name'],
            'applicant_id':int(kwargs.get('applicant_id')),
            'email_from':kwargs['email'],
            'name1':meeting_ids[0].interviewer.name,
            'email_from1':meeting_ids[0].interviewer.email,
            'reschedule_url': reschedule_url

            }
            return request.render("equip3_hr_recruitment_extend.interview_invite_reschedule", data_app)
        return request.render("equip3_hr_recruitment_extend.interview_invite_schedule", res)
    
    
    @http.route(["/open_new_applicant/<int:id>"], type='http', auth="public", website=True, csrf=False)
    def open_new_applicant(self, id, **kw):
        action_id = request.env.ref('equip3_hr_recruitment_extend.hr_applicant_new_tab')
        return request.redirect('/web?&#view_type=form&model=hr.applicant&action=%s&id=%s' % (action_id.id,id))
    
    @http.route(["/open_interview_result/<int:id>"], type='http', auth="public", website=True, csrf=False)
    def open_interview_result(self, id, **kw):
        action_id = request.env.ref('equip3_hr_recruitment_extend.survey_interview_result')
        return request.redirect('/web?&#view_type=form&model=survey.user_input&action=%s&id=%s' % (action_id.id,id))

    @http.route(["/recruiter-submit"], type='http', auth="public", website=True, csrf=False)
    def recruiter_submit(self, **kw):
        values = []
        values_specific =[]
        past_experience_ids = []
        employee_skill_ids = []
        app_email = False
        partner_name = False
        email = False
        app_mobile = False
        if kw.get('past_experience'):
            past_experience = json.loads(kw['past_experience'])
            for data_pe in past_experience:
                start_date_pe = datetime.datetime.strptime(data_pe['start_date'], '%d/%m/%Y')
                start_date_pe = datetime.date.strftime(start_date_pe, "%Y-%m-%d")
                if data_pe.get('end_date'):
                    end_date_pe = datetime.datetime.strptime(data_pe['end_date'], '%d/%m/%Y')
                    end_date_pe = datetime.date.strftime(end_date_pe, "%Y-%m-%d")
                else:
                    end_date_pe = False
                is_currently_work_here = data_pe['is_currently_work_here']
                if is_currently_work_here == 'false':
                    is_currently_work_here  = False

                past_experience_ids.append(
                    (0, 0,{
                        'start_date':start_date_pe,
                        'end_date':end_date_pe,
                        'company_name':data_pe['company_name'],
                        'position':data_pe['position'],
                        'job_descriptions':data_pe['job_descriptions'],
                        'reason_for_leaving':data_pe['reason'],
                        'salary':data_pe['salary'],
                        'is_currently_work_here':is_currently_work_here,
                        'company_telephone_number':data_pe['company_phone'],
                    })
                )

        if kw.get('employee_skill'):
            employee_skill = json.loads(kw['employee_skill'])
            for data_pe in employee_skill:
                employee_skill_ids.append(
                    (0, 0,{
                        'skill_type_id':data_pe['skill_type_id'],
                        'skill_id':data_pe['skill_id'],
                        'skill_level_id':data_pe['skill_level_id'],
                    })
                )
        portal_uploaded_cv_type = ''
        if kw.get('job_id'):
            job = request.env['hr.job'].sudo().search([('id','=',int(kw.get('job_id')))])
            if not job.is_published:
                return request.redirect('/job-close')
            
            for question in job.question_job_position:
                app_q_name = str(question.id)
                setting = request.env['hr.config.settings'].sudo().search([],limit=1)
                if setting.applicant_blacklist:
                    if setting.bl_email:
                        if question.question.id == request.env.ref('equip3_hr_recruitment_extend.job_question_2').id:
                            applicant_bl_email =  request.env['hr.applicant'].sudo().search([('email_from','=',kw.get(app_q_name)),('is_blacklist','=',True)])
                            if applicant_bl_email:
                                return request.redirect('/job-applied')
                            
                    if setting.bl_id_card_number:
                        if question.question.id == request.env.ref('equip3_hr_recruitment_extend.job_question_8').id:
                            applicant_card_number =  request.env['hr.applicant'].sudo().search([('identification_no','=',kw.get(app_q_name)),('is_blacklist','=',True)])
                            if applicant_card_number:
                                return request.redirect('/job-applied')
                            
                    if setting.bl_phone_number:
                        if question.question.id == request.env.ref('equip3_hr_recruitment_extend.job_question_3').id:
                            partner_phone = kw.get(app_q_name)
                            if partner_phone:
                                range = len(partner_phone)
                                if partner_phone[0:3] != "+62":
                                    final_number = "+62"+partner_phone[1:range]
                                applicant_found=  request.env['hr.applicant'].sudo().search([('partner_phone','=',final_number),('is_blacklist','=',True)])
                                if applicant_found:
                                    return request.redirect('/job-applied')
                                
                        if question.question.id == request.env.ref('equip3_hr_recruitment_extend.job_question_4').id:
                            app_mobile = kw.get(app_q_name)
                            if app_mobile:
                                range = len(app_mobile)
                                if app_mobile[0:3] != "+62":
                                    final_number_mobile = "+62"+app_mobile[1:range]
                                applicant_mobile_found=  request.env['hr.applicant'].sudo().search([('partner_mobile','=',final_number_mobile),('is_blacklist','=',True)])
                                if applicant_mobile_found:
                                    return request.redirect('/job-applied')
                                
                
                if question.question.question.lower() == 'what is your email?':
                    app_email = kw.get(app_q_name)
                if question.question.question.lower() == 'what is your mobile number?':
                    app_mobile = kw.get(app_q_name)
                    
                    
                
                    
                if question.question.type != 'file':
                    if question.question.type == 'decimal':
                        q_name =  str(question.id)
                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question' : question.question.question,
                                'answer' : str(float(kw.get(q_name))),
                            })
                            values.append((0,0,dict))
                            if not question.question.global_question or not question.question.is_readonly:
                                values_specific.append((0, 0, dict))
                    elif question.question.type =='many2one':
                        q_name = str(question.id)
                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question': question.question.question,
                                'answer': kw.get(q_name),
                            })
                            values.append((0, 0, dict))
                            if not question.question.global_question or not question.question.is_readonly:
                                values_specific.append((0, 0, dict))
                            
                    elif question.question.type =='drop_down_list':
                        q_name = str(question.id)
                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question': question.question.question,
                                'answer': kw.get(q_name),
                            })
                            values.append((0, 0, dict))
                            if not question.question.global_question or not question.question.is_readonly:
                                values_specific.append((0, 0, dict))
                            
                    elif question.question.type =='date':
                        q_name = str(question.id)
                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question': question.question.question,
                                'answer': str(kw.get(q_name)),
                            })
                            values.append((0, 0, dict))
                            if not question.question.global_question or not question.question.is_readonly:
                                values_specific.append((0, 0, dict))

                    elif question.question.type =='multiple_choice_one_answer':
                        q_name = str(question.id)
                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question': question.question.question,
                                'answer': kw.get(q_name),
                            })
                            values.append((0, 0, dict))
                            if not question.question.global_question:
                                values_specific.append((0, 0, dict))
                    elif question.question.type == 'multiple_choice_multiple_answer':
                        q_name = str(question.id)
                        q_name_replace = str(request.httprequest.form.getlist(q_name)).replace('[','')
                        q_name_replace_final = str(request.httprequest.form.getlist(q_name_replace)).replace(']','')
                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question': question.question.question,
                                'answer': q_name_replace_final,
                            })
                            values.append((0, 0, dict))
                            if not question.question.global_question or not question.question.is_readonly:
                                values_specific.append((0, 0, dict))
                    else:
                        q_name = str(question.id)
                        is_limit_to_one_response_per_email = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.limit_to_one_response_per_email_recruitment')
                        is_email = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_email')
                        is_id_card_number = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_id_card_number')
                        is_phone_number = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_phone_number')
                        max_apply_of_applicant = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.max_apply_of_applicant')
                        if is_email or is_phone_number or is_id_card_number:
                            if question.question.question.lower() == 'what is your email?' and is_email:
                                applicant_email = kw.get(q_name)
                                if kw.get('job_id'):
                                    applicant_job = int(kw.get('job_id'))
                                else:
                                    applicant_job = False

                                check_applicant = request.env['hr.applicant'].sudo().search([('email_from', '=', applicant_email), ('job_id', '=', applicant_job)], limit=1, order='create_date desc')
                                check_email = request.env['hr.applicant'].sudo().search([('email_from', '=', applicant_email), ('job_id', '=', applicant_job)], order='create_date desc')

                                if check_applicant:
                                    range_time_number = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.range_time_number')
                                    range_time_period = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.range_time_period')

                                    # Convert datetime to date
                                    create_date_converted = datetime.datetime.strptime(str(check_applicant.create_date), '%Y-%m-%d %H:%M:%S.%f').date()

                                    if range_time_period == 'days':
                                        min_date_recruitment = create_date_converted + relativedelta(days=int(range_time_number))
                                    elif range_time_period == 'weeks':
                                        min_date_recruitment = create_date_converted + relativedelta(weeks=int(range_time_number))
                                    elif range_time_period == 'months':
                                        min_date_recruitment = create_date_converted + relativedelta(months=int(range_time_number))
                                    else:
                                        min_date_recruitment = create_date_converted + relativedelta(years=int(range_time_number))
                                    
                                    if is_limit_to_one_response_per_email and check_applicant and len(check_email) >= int(max_apply_of_applicant) and min_date_recruitment >= date.today():
                                        return request.render("equip3_hr_recruitment_extend.job_portal_warning_the_same_applicant", {'tanggal': create_date_converted.strftime("%B %d, %Y")})
                            
                            elif question.question.question.lower() == 'what is your mobile number?' and is_phone_number:
                                applicant_phone_number = kw.get(q_name)
                                round_mobile_number = applicant_phone_number.replace(applicant_phone_number[0], '+62')
                                if kw.get('job_id'):
                                    applicant_job = int(kw.get('job_id'))
                                else:
                                    applicant_job = False

                                check_applicant = request.env['hr.applicant'].sudo().search([('partner_mobile', '=', round_mobile_number), ('job_id', '=', applicant_job)], limit=1, order='create_date desc')
                                check_mobile_number = request.env['hr.applicant'].sudo().search([('partner_mobile', '=', round_mobile_number), ('job_id', '=', applicant_job)], order='create_date desc')

                                if check_applicant:
                                    range_time_number = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.range_time_number')
                                    range_time_period = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.range_time_period')

                                    # Convert datetime to date
                                    create_date_converted = datetime.datetime.strptime(str(check_applicant.create_date), '%Y-%m-%d %H:%M:%S.%f').date()

                                    if range_time_period == 'days':
                                        min_date_recruitment = create_date_converted + relativedelta(days=int(range_time_number))
                                    elif range_time_period == 'weeks':
                                        min_date_recruitment = create_date_converted + relativedelta(weeks=int(range_time_number))
                                    elif range_time_period == 'months':
                                        min_date_recruitment = create_date_converted + relativedelta(months=int(range_time_number))
                                    else:
                                        min_date_recruitment = create_date_converted + relativedelta(years=int(range_time_number))
                                    
                                    if is_limit_to_one_response_per_email and check_applicant and len(check_mobile_number) >= int(max_apply_of_applicant) and min_date_recruitment >= date.today():
                                        return request.render("equip3_hr_recruitment_extend.job_portal_warning_the_same_applicant", {'tanggal': create_date_converted.strftime("%B %d, %Y")})

                            elif question.question.question.lower() == 'what is your id card number?' and is_id_card_number:
                                applicant_id_card_number = kw.get(q_name)
                                if kw.get('job_id'):
                                    applicant_job = int(kw.get('job_id'))
                                else:
                                    applicant_job = False

                                check_applicant = request.env['hr.applicant'].sudo().search([('identification_no', '=', applicant_id_card_number), ('job_id', '=', applicant_job)], limit=1, order='create_date desc')
                                check_id_card_number = request.env['hr.applicant'].sudo().search([('identification_no', '=', applicant_id_card_number), ('job_id', '=', applicant_job)], order='create_date desc')
                                if check_applicant:
                                    range_time_number = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.range_time_number')
                                    range_time_period = request.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.range_time_period')

                                    # Convert datetime to date
                                    create_date_converted = datetime.datetime.strptime(str(check_applicant.create_date), '%Y-%m-%d %H:%M:%S.%f').date()

                                    if range_time_period == 'days':
                                        min_date_recruitment = create_date_converted + relativedelta(days=int(range_time_number))
                                    elif range_time_period == 'weeks':
                                        min_date_recruitment = create_date_converted + relativedelta(weeks=int(range_time_number))
                                    elif range_time_period == 'months':
                                        min_date_recruitment = create_date_converted + relativedelta(months=int(range_time_number))
                                    else:
                                        min_date_recruitment = create_date_converted + relativedelta(years=int(range_time_number))
                                    
                                    if is_limit_to_one_response_per_email and len(check_id_card_number) >= int(max_apply_of_applicant) and min_date_recruitment >= date.today():
                                        return request.render("equip3_hr_recruitment_extend.job_portal_warning_the_same_applicant", {'tanggal': create_date_converted.strftime("%B %d, %Y")})
                            

                        if kw.get(q_name):
                            dict = {}
                            dict.update({
                                'question_id':question.id,
                                'question': question.question.question,
                                'answer': kw.get(q_name),
                            })
                            values.append((0, 0, dict))
                            if not question.question.global_question or not question.question.is_readonly:
                                values_specific.append((0, 0, dict))
                if question.question.type == 'file':
                    q_name = str(question.id)
                    if kw.get(q_name):
                        uploaded_cv = kw.get(q_name)
                        portal_uploaded_cv_type = uploaded_cv.content_type
                        file = base64.b64encode(kw.get(q_name).read())
                        dict = {}
                        dict.update({
                            'question_id':question.id,
                            'question' : question.question.question,
                            'file' : file,
                            'file_name':kw.get(q_name).filename
                        })
                        
                        values.append((0,0,dict))
         
            if values or values_specific:       
                outsource_rec = False
                if 'outsource' in request.params:
                    if request.params['outsource'] != '':
                        outsource_id = int(request.params['outsource'])
                        outsource_obj = request.env['hr.recruitment.outsource.master'].sudo().browse(outsource_id)
                        outsource_rec = outsource_obj.id if outsource_obj else False
                applicant = request.env['hr.applicant'].sudo().create({
                    'name': job.name ,
                    # 'partner_name': partner_name,
                    # 'identification_no': id_num,
                    'job_id':  int(kw.get('job_id')) if kw.get('job_id') else False,
                    'cv_type_from_job_portal': portal_uploaded_cv_type,
                    'applicant_question_answer':  values,
                    'applicant_question_answer_spesific':  values_specific,
                    'past_experience_ids':past_experience_ids,
                    'employee_skill_ids':employee_skill_ids,
                    'email_from': app_email,
                    'partner_mobile': app_mobile,
                    'outsource_id': outsource_rec,
                })
        
        return request.redirect('/job-thank-you')

class Surveyedit(Survey):
    
    
    @http.route('/survey/save/files/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def save_file(self, survey_token, answer_token, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        answer = post.get('base64')
        filename = post.get('file_name')
        question = int(post.get('question'))
        answer_sudo.save_lines_files(question, answer,filename)


    @http.route('/survey/save/videofiles/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def save_videofile(self, survey_token, answer_token, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        answer = post.get('base64')
        filename = post.get('file_name')
        question = int(post.get('question'))
        applicant_id = post.get('applicant_id')
        if applicant_id:
            applicant_id = int(applicant_id)
        answer_sudo.save_lines_videofiles(question, answer,filename,applicant_id)

               
              
        


    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):

        """ Submit a page from the survey.
        This will take into account the validation errors and store the answers to the questions.
        If the time limit is reached, errors will be skipped, answers will be ignored and
        survey state will be forced to 'done'"""
        # Survey Validation
        
        

        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']


        if answer_sudo.state == 'done':
            return {'error': 'unauthorized'}

        questions, page_or_question_id = survey_sudo._get_survey_questions(answer=answer_sudo,
                                                                           page_id=post.get('page_id'),
                                                                           question_id=post.get('question_id'))
        
        # if questions.question_type == 'file':
        #     # file = base64.b64encode(post.get(str(questions.id)))
        #     # file = base64.b64encode(post.get(str(questions.id)).read())
        #     print(questions)
            # print(post.get(str(questions.id)))
            

        if not answer_sudo.test_entry and not survey_sudo._has_attempts_left(answer_sudo.partner_id, answer_sudo.email,
                                                                             answer_sudo.invite_token):
            # prevent cheating with users creating multiple 'user_input' before their last attempt
            return {'error': 'unauthorized'}

        if answer_sudo.survey_time_limit_reached or answer_sudo.question_time_limit_reached:
            if answer_sudo.question_time_limit_reached:
                time_limit = survey_sudo.session_question_start_time + relativedelta(
                    seconds=survey_sudo.session_question_id.time_limit
                )
                time_limit += timedelta(seconds=3)
            else:
                time_limit = answer_sudo.start_datetime + timedelta(minutes=survey_sudo.time_limit)
                time_limit += timedelta(seconds=10)
            if fields.Datetime.now() > time_limit:
                # prevent cheating with users blocking the JS timer and taking all their time to answer
                return {'error': 'unauthorized'}



        errors = {}
        # Prepare answers / comment by question, validate and save answers
        for question in questions:            
            inactive_questions = request.env[
                'survey.question'] if answer_sudo.is_session_answer else answer_sudo._get_inactive_conditional_questions()
            if question in inactive_questions:  # if question is inactive, skip validation and save
                continue
            answer, comment = self._extract_comment_from_answers(question, post.get(str(question.id)))
            errors.update(question.validate_question(answer, comment))
            if not errors.get(question.id):
                answer_sudo.save_lines(question, answer, comment)


        if errors and not (answer_sudo.survey_time_limit_reached or answer_sudo.question_time_limit_reached):
            return {'error': 'validation', 'fields': errors}


        if not answer_sudo.is_session_answer:
            answer_sudo._clear_inactive_conditional_answers()

        if answer_sudo.survey_time_limit_reached or survey_sudo.questions_layout == 'one_page':
            answer_sudo._mark_done()
            # Moving applicant to next stage automatically on psychological test
            # answer_sudo.next_stage_on_psy_test()
        elif 'previous_page_id' in post:
            # Go back to specific page using the breadcrumb. Lines are saved and survey continues
            return self._prepare_question_html(survey_sudo, answer_sudo, **post)
        else:
            vals = {'last_displayed_page_id': page_or_question_id}
            if not answer_sudo.is_session_answer:
                next_page = survey_sudo._get_next_page_or_question(answer_sudo, page_or_question_id)
                if not next_page:
                    answer_sudo._mark_done()
                    # Moving applicant to next stage automatically on psychological test
                    # answer_sudo.next_stage_on_psy_test()

            answer_sudo.write(vals)
        input_line = request.env['survey.user_input.line'].sudo().search([('user_input_id', '=', answer_sudo.id)])
        paramater = json.loads(request.httprequest.data)['params']
        if paramater['survey_id'] and paramater['applicant_id'] and paramater['job_position']:
            next_page = survey_sudo._get_next_page_or_question(answer_sudo, page_or_question_id)
            answer_sudo.write({'applicant_id': paramater['applicant_id'],'job_id':paramater['job_position'],'is_use':True})
            applicant = request.env['hr.applicant'].sudo().search(
                [('id', '=', paramater['applicant_id']), ('job_id', '=', paramater['job_position'])])
            answer_sudo.email = applicant.email_from
            applicant.sudo().write({'previous_score': answer_sudo.score_by_amount})
            input_line = request.env['survey.user_input.line'].sudo().search([('user_input_id', '=', answer_sudo.id)])
            if input_line:
                for data in input_line:
                    if data.answer_type == 'numerical_box':
                        data.sudo().write({'applicant_id': paramater['applicant_id'],'value_numerical_box':data.value_numerical_box})

            # if  int(answer_sudo.score_by_amount)  < applicant.stage_replace_id.min_qualification and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' or int(answer_sudo.score_by_amount)  < applicant.stage_replace_id.min_qualification and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers':
            #     applicant.sudo().write({'stage_id': applicant.stage_replace_id.stage_failed.id, 'active': False})
            # else:
            #     next_stage = applicant.job_id.stage_ids.filtered(lambda line:line.sequence == applicant.stage_replace_id.sequence + 1)
            #     if next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' and  int(answer_sudo.score_by_amount) > applicant.stage_replace_id.min_qualification or next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers' and  int(answer_sudo.score_by_amount) > applicant.stage_replace_id.min_qualification:
            #         applicant.sudo().write({'stage_id': next_stage.stage_id.id})
            #         applicant.sudo().message_post()

            
            if applicant.stage_replace_id.survey_id and applicant.stage_replace_id.interview_id:
                prev_input = request.env['survey.user_input'].sudo().search([('survey_id', '=', applicant.stage_replace_id.survey_id.id),('applicant_id', '=', applicant.id),('job_id', '=', applicant.job_id.id),('survey_type', '!=', 'INTERVIEW')], limit=1)
                if survey_sudo.id == applicant.stage_replace_id.interview_id.id:
                    if int(prev_input.score_by_amount) >= applicant.stage_replace_id.min_qualification and int(answer_sudo.skill_score) >= applicant.stage_replace_id.min_skills_score and int(answer_sudo.personality_score) >= applicant.stage_replace_id.min_personality_score and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' or int(prev_input.score_by_amount) >= applicant.stage_replace_id.min_qualification and int(answer_sudo.skill_score) >= applicant.stage_replace_id.min_skills_score and int(answer_sudo.personality_score) >= applicant.stage_replace_id.min_personality_score and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers':
                        next_stage = applicant.job_id.stage_ids.filtered(lambda line:line.sequence == applicant.stage_replace_id.sequence + 1)
                        if next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and answer_sudo.survey_time_limit_reached and answer_sudo.survey_id.scoring_type in ['scoring_without_answers','scoring_with_answers'] and int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification:
                            applicant.sudo().write({'stage_id': next_stage.stage_id.id})
                            applicant.sudo().message_post()
                    else:
                        applicant.sudo().write({'refuse_reason_id': applicant.stage_id.refuse_reason_id.id,'active': False})
                        applicant.send_refuse_mail()
            elif applicant.stage_replace_id.interview_id and not applicant.stage_replace_id.survey_id:
                if int(answer_sudo.skill_score) >= applicant.stage_replace_id.min_skills_score and int(answer_sudo.personality_score) >= applicant.stage_replace_id.min_personality_score and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' or int(answer_sudo.skill_score) >= applicant.stage_replace_id.min_skills_score and int(answer_sudo.personality_score) >= applicant.stage_replace_id.min_personality_score and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers':
                    next_stage = applicant.job_id.stage_ids.filtered(lambda line:line.sequence == applicant.stage_replace_id.sequence + 1)
                    if next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and answer_sudo.survey_time_limit_reached and answer_sudo.survey_id.scoring_type in ['scoring_without_answers','scoring_with_answers'] and int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification:
                        applicant.sudo().write({'stage_id': next_stage.stage_id.id})
                        applicant.sudo().message_post()
                else:
                    applicant.sudo().write({'refuse_reason_id': applicant.stage_id.refuse_reason_id.id,'active': False})
                    applicant.send_refuse_mail()
            elif applicant.stage_replace_id.survey_id and not applicant.stage_replace_id.interview_id:
                if  int(answer_sudo.score_by_amount) < applicant.stage_replace_id.min_qualification and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' or int(answer_sudo.score_by_amount)  < applicant.stage_replace_id.min_qualification and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers' or int(answer_sudo.score_by_amount) < applicant.stage_replace_id.min_qualification and answer_sudo.survey_time_limit_reached and answer_sudo.survey_id.scoring_type in ['scoring_without_answers','scoring_with_answers']:
                    applicant.sudo().write({'refuse_reason_id': applicant.stage_id.refuse_reason_id.id, 'active': False})
                    applicant.send_refuse_mail()
                else:
                    next_stage = applicant.job_id.stage_ids.filtered(lambda line:line.sequence == applicant.stage_replace_id.sequence + 1)
                    if next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and answer_sudo.survey_time_limit_reached and answer_sudo.survey_id.scoring_type in ['scoring_without_answers','scoring_with_answers'] and int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification:
                        applicant.sudo().write({'stage_id': next_stage.stage_id.id})
                        applicant.sudo().message_post()
            else:
                next_stage = applicant.job_id.stage_ids.filtered(lambda line:line.sequence == applicant.stage_replace_id.sequence + 1)
                if next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_without_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and not next_page and answer_sudo.survey_id.scoring_type == 'scoring_with_answers' and  int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification or next_stage and answer_sudo.survey_time_limit_reached and answer_sudo.survey_id.scoring_type in ['scoring_without_answers','scoring_with_answers'] and int(answer_sudo.score_by_amount) >= applicant.stage_replace_id.min_qualification:
                    applicant.sudo().write({'stage_id': next_stage.stage_id.id})
                    applicant.sudo().message_post()

        if str(answer_sudo.survey_type).upper() == 'DISC':
            self.disc_add(answer_sudo)
                
        return self._prepare_question_html(survey_sudo, answer_sudo)

    
    
    def disc_add(self,answer_sudo):
        disc_row_id = []
        question_id = []
        question_m_id = []
        question_l_id = []
        for data in answer_sudo.survey_id.question_and_page_ids.filtered(lambda line:not line.is_question_languange):
            disc_row_id.append(data.id)
        if disc_row_id:
            for page in disc_row_id:
                cek = [answer_line for answer_line in answer_sudo.user_input_line_ids.filtered(lambda line:line.question_id.id == page and line.suggested_answer_id.value == "*" )]
                cek_m = [answer_line for answer_line in answer_sudo.user_input_line_ids.filtered(lambda line:line.question_id.id == page and line.suggested_answer_id.value == "M" )]
                cek_l = [answer_line for answer_line in answer_sudo.user_input_line_ids.filtered(lambda line:line.question_id.id == page and line.suggested_answer_id.value == "L" )]
                if len(cek)>3:
                    for line in cek:
                        question_id.append(line.question_id.id)
                        line.unlink()

                else:
                    for line in cek:
                        line.unlink()
                if cek_m and len(cek) ==3:
                    for line in cek_m:
                        question_m_id.append(line.question_id.id)
                if cek_l and len(cek) ==3:
                    for line in cek_l:
                        question_l_id.append(line.question_id.id)
            if question_id:
                for id in set(question_id):
                    answer_q = request.env['survey.question.answer'].sudo().search([('value','=','M')],limit=1)
                    request.env['survey.user_input.line'].sudo().create({'user_input_id':answer_sudo.id,'suggested_answer_id':answer_q.id,'answer_type':'suggestion','question_id':id,'is_skip':True})
                    answer_ql = request.env['survey.question.answer'].sudo().search([('value', '=', 'L')], limit=1)
                    request.env['survey.user_input.line'].sudo().create(
                        {'user_input_id': answer_sudo.id, 'suggested_answer_id': answer_ql.id, 'answer_type': 'suggestion',
                            'question_id': id,'is_skip':True})
            if question_m_id:
                for id in set(question_m_id):
                    answer_ql = request.env['survey.question.answer'].sudo().search([('value', '=', 'L')], limit=1)
                    request.env['survey.user_input.line'].sudo().create(
                        {'user_input_id': answer_sudo.id, 'suggested_answer_id': answer_ql.id, 'answer_type': 'suggestion',
                            'question_id': id,'is_skip':True})
            if question_l_id:
                for id in set(question_l_id):
                    answer_ql = request.env['survey.question.answer'].sudo().search([('value', '=', 'M')], limit=1)
                    request.env['survey.user_input.line'].sudo().create(
                        {'user_input_id': answer_sudo.id, 'suggested_answer_id': answer_ql.id, 'answer_type': 'suggestion',
                            'question_id': id,'is_skip':True})
                    
        

    @http.route('/survey/start/<string:survey_token>', type='http', auth='public', website=True)
    def survey_start(self, survey_token, answer_token=None, email=False, surveyId=None,applicantId=None,jobPosition=None,trainingId=None,employeeId=None, **post):
        """ Start a survey by providing
         * a token linked to a survey;
         * a token linked to an answer or generate a new token if access is allowed;
        """
        # Get the current answer token from cookie
        if post.get('survey_id'):
            print('llllllllllllll')
            surveyId = post.get('survey_id')
        if not answer_token:
            answer_token = request.httprequest.cookies.get('survey_%s' % survey_token)

        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            try:
                answer_sudo = survey_sudo._create_answer(user=request.env.user, email=email)
            except UserError:
                answer_sudo = False

        if not answer_sudo:
            try:
                survey_sudo.with_user(request.env.user).check_access_rights('read')
                survey_sudo.with_user(request.env.user).check_access_rule('read')
            except:
                return werkzeug.utils.redirect("/")
            else:
                return request.render("survey.survey_403_page", {'survey': survey_sudo})
        print(surveyId,applicantId,jobPosition,'jobPositionjobPositionjobPosition',post)

        if survey_sudo and applicantId and jobPosition:
            query_statement = """SELECT id FROM survey_user_input WHERE job_id = %s AND survey_id = %s and applicant_id = %s AND is_use IS TRUE"""
            request.env.cr.execute(query_statement, [jobPosition,survey_sudo.id,applicantId])
            hr_applicant_query = request._cr.dictfetchone()
            if hr_applicant_query:
                return request.render("equip3_hr_recruitment_extend.test_completed_page", {'survey': survey_sudo})
            return request.redirect('/survey/%s/%s?surveyId=%s&applicantId=%s&jobPosition=%s' % (survey_sudo.access_token, answer_sudo.access_token,survey_sudo.id,applicantId,jobPosition))
        # if surveyId and trainingId and employeeId:
        #     return request.redirect('/survey/%s/%s?surveyId=%s&trainingId=%s&employeeId=%s' % (survey_sudo.access_token, answer_sudo.access_token,surveyId,trainingId,employeeId))

        return request.redirect('/survey/%s/%s' % (survey_sudo.access_token, answer_sudo.access_token))




    
