from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import json
from ....restapi.controllers.helper import *
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.addons.website_slides.controllers.main import *


class LmsWebsiteSlides(WebsiteSlides,RestApi):
    @http.route('/api/slides/slide/quiz/submit', type="json", auth="public")
    def api_slide_quiz_submit(self,**kw):
        request_data = request.jsonrequest
        slide_id = request_data.get('slide_id')
        answer_ids = request_data.get('answer_ids')
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        
        slide = fetch_res['slide']
        if slide.user_membership_id.sudo().completed:
            self._channel_remove_session_answers(slide.channel_id, slide)
            # return self.get_response(200, '200', {"code":200,
            #                                       "error":"slide_quiz_done"
            #                                       })
            
        all_questions = request.env['slide.question'].sudo().search([('slide_id', '=', slide.id)])
        user_answers = request.env['slide.answer'].sudo().search([('id', 'in', answer_ids)])
        if user_answers.mapped('question_id') != all_questions:
            return self.get_response(200, '200', {"code":200,
                                                  "error":"Semua jawaban harus di input !"
                                                  })

        user_bad_answers = user_answers.filtered(lambda answer: not answer.is_correct)
        self._set_viewed_slide(slide, quiz_attempts_inc=True)
        quiz_info = self._get_slide_quiz_partner_info(slide, quiz_done=True)
        rank_progress = {}
        if not user_bad_answers:
            rank_progress['previous_rank'] = self._get_rank_values(request.env.user)
            slide._action_set_quiz_done()
            slide.action_set_completed()
            rank_progress['new_rank'] = self._get_rank_values(request.env.user)
            rank_progress.update({
                'description': request.env.user.rank_id.description,
                'last_rank': not request.env.user._get_next_rank(),
                'level_up': rank_progress['previous_rank']['lower_bound'] != rank_progress['new_rank']['lower_bound']
            })
            
        self._channel_remove_session_answers(slide.channel_id, slide)
        return self.get_response(200, '200', {
            'answers': [{
                    'id':answer.question_id.id,
                    'is_correct': answer.is_correct,
                    'comment': answer.comment
                } for answer in user_answers
            ],
            'completed': slide.user_membership_id.sudo().completed,
            'channel_completion': slide.channel_id.completion,
            'quizKarmaWon': quiz_info['quiz_karma_won'],
            'quizKarmaGain': quiz_info['quiz_karma_gain'],
            'quizAttemptsCount': quiz_info['quiz_attempts_count'],
            'rankProgress': rank_progress,
        })
    
class Equip3HumanResourceLmsDashboard(RestApi):
    @route(['/api/lms/quiz/<int:channel_id>'],auth='user', type='http', methods=['get'])
    def api_get_quiz(self,channel_id=None,id=None, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'slide.slide'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        domain = [('channel_id','=',channel_id)]
        if kw.get('search'):
            domain.append(('name','ilike',kw.get('search')))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                     'datas',
                                                                                     'url',
                                                                                     'external_url',
                                                                                     'survey_id',
                                                                                     'description',
                                                                                     'slide_type',
                                                                                     'filename',
                                                                                     'question_ids'
                                                                                ],
                            "order":"sequence asc",
                            "offset":offset,
                            "limit":PAGE_DATA_LIMIT
                            }
        try:
            read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
            response_data = json.loads(read_record.data)
            if not obj in response_data:
                return self.record_not_found()  
        except json.decoder.JSONDecodeError:
            return self.get_response(500, '200', {"code":500,
                                                  "error":read_record.data
                                                  })
            
        for data_question in response_data[obj]:
            if 'slide_type' in data_question:
                if data_question['slide_type'] == 'document':
                    if data_question['datas']  and not data_question['filename']:
                        data_question['file_name'] =  data_question['name'] + '.pdf'
                        
                    elif data_question['datas'] and data_question['filename']:
                        data_question['file_name'] =  data_question['filename']
                        
                    else:
                        data_question['file_name'] =  False
                data_question.pop('filename')
                        
            fetch_res = self._fetch_slide(data_question['id'])
            slide = fetch_res['slide']
            data_question.update(self._get_slide_quiz_data_lms(slide))
            data_question.pop('question_ids')
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    def _get_slide_quiz_data_lms(self, slide):
        slide_completed = slide.user_membership_id.sudo().completed
        values = {
            'slide_questions': [{
                'id': question.id,
                'question': question.question,
                'answer_ids': [{
                    'id': answer.id,
                    'text_value': answer.text_value,
                    'is_correct': answer.is_correct if slide_completed  else None,
                    'comment': answer.comment
                } for answer in question.sudo().answer_ids],
            } for question in slide.question_ids]
        }
        if 'slide_answer_quiz' in request.session:
            slide_answer_quiz = json.loads(request.session['slide_answer_quiz'])
            if str(slide.id) in slide_answer_quiz:
                values['session_answers'] = slide_answer_quiz[str(slide.id)]
        values.update(self._get_slide_quiz_partner_info(slide))
        return values

    @route(['/api/lms/course','/api/lms/course/<int:id>'],auth='user', type='http', methods=['get'])
    def api_lms_course(self,id=None, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'slide.channel'
        auth, user, invalid = self.valid_authentication(kw)
        filter_str = f"lambda line:line"
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        if kw.get("is_ongoing"):
            filter_str = filter_str + f" and line.completion >= 0 and line.completion < 100"
            
        if kw.get("is_completed"):
            filter_str = filter_str + f" and line.completion == 100"
            
        domain = []
        if kw.get('search'):
            domain.append(('name','ilike',kw.get('search')))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['name',
                                   'description',
                                   'image_1920',
                                   'completion',
                                   'total_time',
                                   'tag_ids',
                                   'rating_avg_stars',
                                   'user_id',
                                   'members_count',
                                   'slide_ids'
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                    'image_1920',
                                                                                    'completion',
                                                                                    'total_time',
                                                                                    'tag_ids',
                                                                                    ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
        try:
            read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
            response_data = json.loads(read_record.data)
            if not obj in response_data:
                return self.record_not_found()
            
        except json.decoder.JSONDecodeError:
            return self.get_response(500, '200', {"code":500,
                                                  "error":read_record.data
                                                  })
            
        if not id:
            for data in response_data[obj]:
                if 'total_time' in data:
                    data['total_time'] = str(timedelta(hours=data['total_time']))
                if 'tag_ids' in data:
                    if len(data['tag_ids']) >= 1:
                        data['tag_ids'] = self.convert_one2many('slide.channel.tag',{"fields":['name'],"ids":','.join(str(id) for id in data['tag_ids'])},user)
        if id:
            if 'total_time' in response_data[obj]:
                    response_data[obj]['total_time'] = str(timedelta(hours=response_data[obj]['total_time']))
                    
            if 'tag_ids' in response_data[obj]:
                if len(response_data[obj]['tag_ids']) >= 1:
                    response_data[obj]['tag_ids'] = self.convert_one2many('slide.channel.tag',{"fields":['name'],"ids":','.join(str(id) for id in response_data[obj]['tag_ids'])},user)
                    
            if 'slide_ids' in response_data[obj]:
                if len(response_data[obj]['slide_ids']) >= 1:
                    response_data[obj]['slide_ids'] = self.convert_one2many('slide.slide',{"fields":['name','completion_time','question_ids','date_published'],"ids":','.join(str(id) for id in response_data[obj]['slide_ids'])},user)   
                    for data_slide in response_data[obj]['slide_ids']:
                        if 'completion_time' in data_slide:
                            data_slide['completion_time'] = str(timedelta(hours=data_slide['completion_time']))
         
                        if 'question_ids' in data_slide:
                            if len(data_slide['question_ids']) >= 1:
                                data_slide['question_ids'] = self.convert_one2many('slide.question',{"fields":['question','answer_ids'],"ids":','.join(str(id) for id in data_slide['question_ids'])},user)
                                
                                for question in data_slide['question_ids']:
                                    if 'answer_ids' in question:
                                        question['question_count'] = len(question['answer_ids'])
                                        
                message = request.env['mail.message'].sudo().search([('model','=',obj),('res_id','=',id),('message_type','=','comment')])
                if message:
                    response_data[obj]['rating_ids'] = [{
                        'id':ms.id,
                        'author':ms.author_id.name,
                                                         'image':ms.author_id.image_1920.decode("utf-8") if ms.author_id.image_1920 else '-',
                                                         'comment':ms.body,
                                                         'create_date':ms.create_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                                         'rating':ms.rating_value
                                                         } for ms in message]
                    for child in response_data[obj]['rating_ids']:
                        if 'id' in child:
                             child_message = request.env['rating.rating'].sudo().search([('message_id','=',child['id'])])
                             if child_message:
                                 child['child_ids'] = [{'id':ms.id,
                                                        'author':ms.partner_id.name,
                                                         'image':ms.partner_id.image_1920.decode("utf-8") if ms.partner_id.image_1920 else '-',
                                                         'create_date':ms.create_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                                         'comment':ms.publisher_comment,
                                                         } for ms in child_message]
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    @route('/api/lms/dashboard',auth='user', type='http', methods=['get'])
    def api_lms_dashboard(self, **kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        next_rank_id = request.env.user.next_rank_id or request.env.user._get_next_rank()
        rank_list = []
        ranks_obj =  request.env['gamification.karma.rank'].sudo().search([])
        if not ranks_obj:
            return self.record_not_found()
        for data in ranks_obj:
            rank_list.append({'id':data.id,
                              "name":data.name,
                              "karma":data.karma_min,
                              "image_1920":data.image_1920.decode("utf-8") if data.image_1920 else '-'
                              })
        histories =  request.env['training.histories'].sudo().search([('state','not in',['to_do'])],limit=10,order='id asc')
        first_date = '-'
        if histories:
            first_date = min([data.start_date for data in histories])
            first_date= first_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        forum_post = request.env['forum.post'].sudo().search_count([('create_uid','=',request.env.user.id),('forum_id.slide_channel_ids','!=',False)])
        forum_post_obj = request.env['forum.post'].sudo().search([('create_uid','=',request.env.user.id),('forum_id.slide_channel_ids','!=',False)])
        followed_count = request.env['forum.post'].sudo().search_count([('message_partner_ids', '=', user.partner_id.id)])
        tagged_count = request.env['forum.post'].sudo().search_count([('tag_ids.message_partner_ids', '=', user.partner_id.id)])
        favorite_count = sum([data.favourite_count for data in forum_post_obj])
        slide_channel_obj_ids = request.env['slide.channel'].sudo().search([('completion','=',100),('partner_ids', '=', request.env.user.partner_id.id)])
        courses = request.env['slide.channel.partner'].sudo().search([('partner_id', '=', user.partner_id.id)])
        courses_completed = courses.filtered(lambda c: c.completed)
        courses_ongoing = courses - courses_completed
        course_ids = []
        bookmark_ids = []
        if slide_channel_obj_ids:
            course_ids.extend({
                            'id':data.id,
                            'name':data.name,
                           'image_1920':data.image_1920.decode("utf-8") if data.image_1920 else '-',
                           'completion':data.completion,
                           'total_time':str(timedelta(hours=data.total_time)),
                           'tag_ids':[{'name':data_tag.name} for data_tag in data.tag_ids]
                           
                           
                           } for data in slide_channel_obj_ids)
        if courses_ongoing:
            bookmark_ids.extend({'name':data.channel_id.name,
                           'image_1920':data.channel_id.image_1920.decode("utf-8") if data.channel_id and data.channel_id.image_1920 else '-',
                           'completion':data.channel_id.completion,
                           'total_time':str(timedelta(hours=data.channel_id.total_time)),
                           'tag_ids':[{'name':data_tag.name} for data_tag in data.channel_id.tag_ids]
                           
                           
                           } for data in courses_ongoing)
            
        response = {
                    "user_point":user.karma,
                    "rank_name":user.rank_id.name,
                    "image_1920":user.rank_id.image_1920.decode("utf-8") if user.rank_id.image_1920 and user.rank_id  else '-',
                    "next_rank_name":next_rank_id.name,
                    "next_rank_id":next_rank_id.karma_min,
                    'rank_list':rank_list,
                    'join_date':first_date,
                    'my_post':forum_post,
                    'favorite_count':favorite_count,
                    'followed_count':followed_count,
                    'tagged_count':tagged_count,
                    'course_ids':course_ids
                    
                    } 
               
        return self.get_response(200, '200', {"code":200,"data":response})