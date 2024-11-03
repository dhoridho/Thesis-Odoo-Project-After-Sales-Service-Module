from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import json
from ....restapi.controllers.helper import *

class Equip3HumanResourceLmsForum(RestApi):
    @http.route(['/api/lms/forum/create'],type='json', auth="user", methods=['POST'])
    def post_create_lms(self, **kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        post_tag_ids = [(6,0,request_data.get('post_tags'))]
        parent_post = False
        if request_data.get('parent_id'):
            parent_post = request.env['forum.post'].sudo().search([('id','=',request_data.get('parent_id'))])
            
        new_question = request.env['forum.post'].sudo().create({
            'forum_id': request_data.get('forum_id'),
            'name': request_data.get('post_name') or (parent_post and 'Re: %s' % (parent_post.name or '')) or '',
            'content': request_data.get('content', False),
            'parent_id': parent_post and parent_post.id or False,
            'tag_ids': post_tag_ids
        })
        if not new_question:
                return self.update_create_failed() 
              
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Post Suscessfull"})
        
    
    @http.route(['/api/lms/forum'],type="http", auth="user",methods=['get'])
    def get_forum(self, id= None,**kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'forum.forum'
        domain = []
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
        
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),
                         "fields":['name','image_1920'],
                        "offset":offset,
                        "limit":PAGE_DATA_LIMIT if not limit else limit
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
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        response =  {"code":200,
                     "data":response_data[obj],
                     "page_total":page_total if not id else 0
                     }
        return self.get_response(200, '200',response)
    
    @http.route(['/api/lms/tags'],type="http", auth="user",methods=['get'])
    def get_tags(self, id= None,**kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'forum.tag'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                        "offset":offset,
                        "limit":PAGE_DATA_LIMIT if not limit else limit
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
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        response =  {"code":200,
                     "data":response_data[obj],
                     "page_total":page_total if not id else 0
                     }
        return self.get_response(200, '200',response)
    
    @route('/api/lms/forum_post',auth='user', type='http', methods=['get'])
    def api_lms_forum_post(self, **kw):
        is_unaswered =  kw.get('is_unaswered')
        course_id =  kw.get('course_id')
        forum_id =  kw.get('forum_id')
        auth, user, invalid = self.valid_authentication(kw)
        domain = [('parent_id','=',False),('active','=',True)]
        if forum_id:
            domain.append(('forum_id','=',int(forum_id)))
        if course_id:
            domain.append(('forum_id.slide_channel_id','=',int(course_id)))
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        forum_post_list = []
        post_obj =  request.env['forum.post'].sudo().search(domain)
        if not post_obj:
            return self.record_not_found()
        for data in post_obj:
            data_dict = {'id':data.id,
                         "avatar":data.create_uid.image_128.decode("utf-8") if data.create_uid.image_128 else "-",
                         'author_id':data.create_uid.name, 
                         "name":data.name,
                         "forum_id":[data.forum_id.id,data.forum_id.name] if data.forum_id else [],
                         "content":data.content,
                         "vote_count":data.vote_count,
                         'create_date':data.create_date.strftime("%m/%d/%Y"),
                         "course_id":[data.forum_id.slide_channel_id.id,data.forum_id.slide_channel_id.name] if data.forum_id.slide_channel_id else [],
                         "tag_ids":[{'id':tag.id,'name':tag.name} for tag in data.tag_ids]
                         }
            
            self.get_post_child_ids(data_dict,data)
            if is_unaswered:
                if 'answer_ids' not in data_dict:
                    forum_post_list.append(data_dict)
            else:             
                forum_post_list.append(data_dict)
        return self.get_response(200, '200', {"code":200,"data":forum_post_list})
    
    def get_post_child_ids(self,data_dict,post_obj):
        chils_ids = []
        comment_ids = []
        childs_obj = request.env['forum.post'].search([('parent_id','=',post_obj.id)])
        if post_obj.website_message_ids:
            for data in post_obj.website_message_ids:
                comment_dict = {'id':data.id,
                                    'author_id':data.create_uid.name, 
                                    "avatar":data.create_uid.image_128.decode("utf-8") if data.create_uid.image_128 else "-",
                                    "content":data.body,
                                    # "vote_count":data.vote_count,
                                    'create_date':data.create_date.strftime("%m/%d/%Y")
                                    }
                comment_ids.append(comment_dict)
                data_dict['comment_ids'] = comment_ids
        if childs_obj:
            for data in childs_obj:
                child_dict = {'id':data.id,
                                    'author_id':data.create_uid.name, 
                                    "avatar":data.create_uid.image_128.decode("utf-8") if data.create_uid.image_128 else "-",
                                    "name":data.name,
                                    "content":data.content,
                                    'create_date':data.create_date.strftime("%m/%d/%Y")
                                    }
                chils_ids.append(child_dict)
                self.get_post_child_ids(child_dict,data)
                data_dict['answer_ids'] = chils_ids
 

            
              
                    