# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import pytz
import json


class Equip3HumanResourceRestapi(RestApi):
    @route('/api/user/dashboard',auth='user', type='http', methods=['get'])
    @authenticate
    def api_user_dashboard(self, **kw):
        leave_balance = 0
        leave_assigned = 0
        leave_balances = request.env['hr.leave.balance'].sudo().search(
                    [('employee_id.user_id', '=', request.env.user.id)])
        if leave_balances:
            for leave_b in leave_balances:
                if leave_b.holiday_status_id.is_dashboard:
                    leave_balance += leave_b.remaining
        leave_assigneds = request.env['hr.leave.balance'].sudo().search(
            [('employee_id.user_id', '=', request.env.user.id)])
        if leave_assigneds:
            for leave_as in leave_assigneds:
                if leave_as.holiday_status_id.is_dashboard:
                    leave_assigned += leave_as.assigned
                    leave_assigned += leave_as.bring_forward
                    leave_assigned += leave_as.extra_leave 
        query = """
        select count(ha.id) from hr_attendance ha WHERE ha.create_date  >= current_date - interval '30' day and  ha.create_date  <= current_date and ha.employee_id = %s
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        attendance = request.env.cr.dictfetchone()
        expense_total = 0
        query = """
        select SUM(he.total_amount) from hr_expense he where he.employee_id = %s
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        expense = request.env.cr.dictfetchone()
        try:
            if 'sum' in expense:
                expense_total += expense['sum']
        except TypeError:
            pass
        query = """
        select count(hc.id) from hr_contract hc where hc.employee_id = %s
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        contract = request.env.cr.dictfetchone()
    
        travel_count = 0
        query = """
        select count(tr.id) from travel_request tr WHERE tr.employee_id = %s
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        travel = request.env.cr.dictfetchone()
        if 'count' in travel:
            travel_count = travel['count']
            
        travel_approve = 0
        query = """
        select count(tr.id) from travel_request tr WHERE tr.employee_id = %s AND tr.state = 'approved'
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        travel_approve_obj = request.env.cr.dictfetchone()
        if 'count' in travel_approve_obj:
            travel_approve = travel_approve_obj['count']
            
        travel_ca_submitted = 0
        query = """
        select count(tr.id) from travel_request tr WHERE tr.employee_id = %s AND tr.state = 'cash_advance_submitted'
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        travel_ca_submitted_obj = request.env.cr.dictfetchone()
        if 'count' in travel_ca_submitted_obj:
            travel_ca_submitted = travel_ca_submitted_obj['count']
            
        travel_submitted = 0
        query = """
        select count(tr.id) from travel_request tr WHERE tr.employee_id = %s AND tr.state = 'submitted'
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        travel_submitted_obj = request.env.cr.dictfetchone()
        if 'count' in travel_submitted_obj:
            travel_submitted = travel_submitted_obj['count']
               
        ca_total = 0
        cash_advance = request.env['vendor.deposit'].search([('employee_id','=',request.env.user.employee_id.id),('state','=','approved')])
        if cash_advance:
            ca_total = sum([data.amount for data in cash_advance])
        
        loan_total = 0
        employee_loan = request.env['employee.loan.details'].search([('user_id','=',request.env.user.id),('state','=','approved')])
        if employee_loan:
            loan_total = sum([data.principal_amount for data in employee_loan])
            
        
        training_total = 0
        query = """
        select count(th.id) from training_histories th where th.employee_id = %s and state in ('to_do','on_progress')
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        training = request.env.cr.dictfetchone()
        if  'count' in training:
            training_total = training['count']
        
        return self.get_response(200, '200', {"code":200, 
                                              "employee_image":request.env.user.employee_id.image_1920.decode("utf-8") if request.env.user.employee_id.image_1920 else '-',
                                              "leaves": f"{leave_balance}/{leave_assigned}",
                                              "employee_name":request.env.user.employee_id.name,
                                              "attendance":attendance['count'],
                                              "expense":float(expense_total),
                                              "contract":contract['count'],
                                              "travel":travel_count,
                                              "travel_approve":travel_approve,
                                              "travel_ca_submitted":travel_ca_submitted,
                                              "travel_submitted":travel_submitted,
                                              "cash_advance":ca_total,
                                              "loan":loan_total,
                                              "training":training_total

                                              })
        
    
    @route(['/api/user/announcement','/api/user/announcement/<int:id>'],auth='user', type='http', methods=['get'])
    def get_user_dashboard_annountcement(self,id=None,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        hr_announcement_ids = request.env['hr.announcement'].sudo().search([('state','=','submitted')]).filtered(lambda line:request.env.user.employee_id.id in line.employee_ids.ids  or 
                                                                                                                 request.env.user.employee_id.department_id.id in line.department_ids.ids  or 
                                                                                                                 request.env.user.employee_id.job_id.id in line.position_ids.ids or line.is_announcement)
        if not hr_announcement_ids:
            return self.record_not_found()
        request_param = {"fields":['announcement_reason','announcement','date_start','date_end']}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in hr_announcement_ids),"order":"id desc","fields":['announcement_reason','announcement','date_start','date_end'],"limit":5}
        read_record = self.perform_request('hr.announcement',id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'hr.announcement' in response_data:
           return self.record_not_found()
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data['hr.announcement']
                                              })
        
        
        
    @route(['/api/user/contract','/api/user/contract/<int:id>'],auth='user', type='http', methods=['get'])
    def get_user_contract(self,id=None,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        contract_ids = request.env['hr.contract'].sudo().search([('employee_id','=',request.env.user.employee_id.id)])
        if not contract_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                   'name',
                                   'job_id',
                                   'employee_id',
                                   'department_id',
                                   'parent_id',
                                   'work_location_id',
                                   'type_id','struct_id',
                                   'struct_pesangon_id',
                                   'contract_template','date_start','date_end',
                                   'resource_calendar_id',
                                   'schedule_pay',
                                   'hr_responsible_id',
                                   'create_date',
                                   'create_uid',
                                   'wage',
                                   'rapel_date',
                                   'daily_wage',
                                   'hourly_wage',
                                   'other_allowance_1',
                                   'other_allowance_2',
                                   'other_allowance_3',
                                   'other_allowance_5',
                                   'other_allowance_6',
                                   'other_allowance_7',
                                   'other_allowance_8',
                                   'other_allowance_9'
                                   
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in contract_ids),"fields":['state','name','job_id','wage'],"order":"id desc"}
        read_record = self.perform_request('hr.contract',id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'hr.contract' in response_data:
           return self.record_not_found()
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data['hr.contract']
                                              })
    
    @route(['/api/user/onboarding','/api/user/onboarding/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_onboarding(self,id=None,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line.employee_name.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"
            
        domain = []
        if kw.get("search"):
            domain.append('|')
            domain.append(('name','ilike',kw.get("search")))
            domain.append(('orientation_id.checklist_name','ilike',kw.get("search")))
        
        orientation_ids = request.env['employee.orientation'].sudo().search(domain).filtered(eval(filter_str))
        
        if not orientation_ids:
            return self.record_not_found()
        request_param = {"fields":[
                            'name',
                            'employee_name',
                            'job_id',
                            'parent_id',
                            'employee_company',
                            'responsible_user',
                            'date',
                            'state',
                            'department',
                            'orientation_id',
                            'responsible_user',
                            'orientation_request',
                            'elearning_line_ids',
                            'note_id'
                                
                                ]}
        if not id:
            request_param = {"fields":['employee_name',
                                    'name',
                                    'state',
                                    'department',
                                    'orientation_id',
                                    'responsible_user',
                                    ],"order":"id desc",
                                    "ids":','.join(str(data.id) for data in orientation_ids),
                             }
        
        read_record = self.perform_request('employee.orientation',id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'employee.orientation' in response_data:
            return self.record_not_found()
        if id:
            if len(response_data['employee.orientation']['orientation_request']) >= 1:
                response_data['employee.orientation']['orientation_request'] = self.convert_one2many('orientation.request',{"fields":['request_name','state','partner_id','request_expected_date'],"ids":','.join(str(data) for data in response_data['employee.orientation']['orientation_request'])},user)
            if len(response_data['employee.orientation']['elearning_line_ids']) >= 1:
                response_data['employee.orientation']['elearning_line_ids'] = self.convert_one2many('elearning.line',{"fields":['course_id','user_id','expected_date','progress','state'],"ids":','.join(str(data) for data in response_data['employee.orientation']['elearning_line_ids'])},user)
       
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data['employee.orientation']
                                              })
    
    
    
    @route('/api/employee/detail',auth='user', type='http', methods=['get'])
    def employee_detail(self,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        env = request.env
        contract_date = "-"
        contract = request.env['hr.contract'].search([('employee_id','=',env.user.employee_id.id)],order="id DESC",limit=1)
        if contract:
            contract_date = contract.date_start.strftime("%m/%d/%Y")
        leave_balance = 0
        leave_assigned = 0
        leave_balances = request.env['hr.leave.balance'].sudo().search(
                    [('employee_id.user_id', '=', request.env.user.id)])
        if leave_balances:
            for leave_ba in leave_balances:
                if leave_ba.holiday_status_id.is_dashboard:
                    leave_balance += leave_ba.remaining
        leave_assigneds = request.env['hr.leave.balance'].sudo().search(
            [('employee_id.user_id', '=', request.env.user.id)])
        if leave_assigneds:
            for leave_as in leave_assigneds:
                if leave_as.holiday_status_id.is_dashboard:
                    leave_assigned += leave_as.assigned
                    leave_assigned += leave_as.bring_forward
                    leave_assigned += leave_as.extra_leave 
                    
        employee_probation = "-"
        probation = request.env['employee.probation'].search([('employee_id','=',env.user.employee_id.id)],order="id DESC",limit=1)
        if probation:
            employee_probation =  probation.start_date.strftime("%m/%d/%Y")
            
        document_total = 0
        query = """
        select count(hed.id) from hr_employee_document hed where hed.employee_ref = %s 
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        document = request.env.cr.dictfetchone()
        if  'count' in document:
            document_total = document['count']
            
            
        timesheet_total = 0
        query = """
        select count(ht.id) from hr_timesheet ht where ht.employee_id = %s AND extract(YEAR FROM ht.start_date) = extract(YEAR FROM now()) and extract(MONTH FROM ht.start_date) = extract(MONTH FROM now()) AND state = 'approved'
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        timesheet = request.env.cr.dictfetchone()
        if  'count' in timesheet:
            timesheet_total = timesheet['count']

        return self.get_response(200, '200', {"code":200, 
                                              "employee_image":env.user.employee_id.image_1920.decode("utf-8"),
                                              "name":env.user.name,
                                              "job_position":env.user.employee_id.job_title,
                                              "entry_progress":env.user.employee_id.entry_progress,
                                              "exit_progress":env.user.employee_id.exit_progress,
                                              "contract_date":contract_date,
                                              "leaves": f"{leave_balance}/{leave_assigned}",
                                              "payslip_count ":env.user.employee_id.payslip_count,
                                              "employee_probation":employee_probation,
                                              "document_total":document_total,
                                              "timesheet_total":timesheet_total,
                                              "biodata":{
                                                  "employee_id":env.user.employee_id.sequence_code ,
                                                  "work_mobile":env.user.employee_id.mobile_phone,
                                                  "work_phone":env.user.employee_id.work_phone,
                                                  "work_email":env.user.employee_id.work_email,
                                                  "company_id":{
                                                      "id":env.user.employee_id.company_id.id,
                                                      "name":env.user.employee_id.company_id.name
                                                      
                                                  },
                                                  "department_id":{
                                                      "id":env.user.employee_id.department_id.id,
                                                      "name":env.user.employee_id.department_id.name
                                    
                                                      },
                                                  "manager_id":{
                                                      "id":env.user.employee_id.parent_id.id,
                                                      "name":env.user.employee_id.parent_id.name
                                                      
                                                      },
                                                  "coach_id":{
                                                      "id":env.user.employee_id.coach_id.id,
                                                      "name":env.user.employee_id.coach_id.name
                                                      
                                                  },
                                                  "date_of_joining":env.user.employee_id.date_of_joining.strftime("%d %B, %Y") if env.user.employee_id.date_of_joining else "-"
                                                  
                                              },
                                            "resune_line_ids":[
                                                
                                                    {
                                                    "type_id":{"id":data.line_type_id.id,
                                                               "name":data.line_type_id.name
                                                        },
                                                    "company":data.name,
                                                     "description":data.description,
                                                     "date_start":data.date_start.strftime("%m/%d/%Y"),
                                                     "date_end":data.date_end.strftime("%m/%d/%Y") if data.date_end else "Current"
                                                     
                                                     } for data in env.user.employee_id.resume_line_ids   
                                                    ],
                                            "employee_skill_ids":[{"skill_type_id":{"id":data.skill_type_id.id,
                                                                                    "name":data.skill_type_id.name
                                                                                    },
                                                                   "skill_id":{"id":data.skill_id.id,
                                                                               "name":data.skill_id.name
                                                                               },
                                                                   "skill_level_id":{"id":data.skill_level_id.id,
                                                                                     "name":data.skill_level_id.name
                                                                                     
                                                                                     },
                                                                   "level_progress":data.level_progress
                                                                   
                                                                   } for data in env.user.employee_id.employee_skill_ids],
                                            "badge_ids":[{"image":data.badge_id.image_1920.decode("utf-8") if data.badge_id.image_1920 else '-',
                                                          "badge":data.badge_id.name,
                                                          "create_uid":{"id":data.create_uid.id,
                                                                     "name":data.create_uid.name
                                                                     },
                                                          "create_date":data.create_date.strftime("%m/%d/%Y") if data.create_date else "-"
                                                          
                                                          } for data in  env.user.employee_id.badge_ids ],
                                            "loan_ids":[{"number":data.name,
                                                         "state":data.state,
                                                         "applied_date":data.date_applied.strftime("%m/%d/%Y") if data.date_applied else "-",
                                                         "approved__date":data.date_approved.strftime("%m/%d/%Y") if data.date_approved else "-",
                                                         "principal_amount":data.principal_amount,
                                                         "total_amount_paid":data.total_amount_paid,
                                                         "final_total":data.final_total,
                                                         "total_amount_due":data.total_amount_due,
                                                         "loan_type":{'id':data.loan_type.id,
                                                                      'name':data.loan_type.name
                                                                      },
                                                         "int_rate":data.int_rate
                                                         } for data in env.user.employee_id.loan_ids],
                                            "loan_policy":[{"name":data.name,
                                                            "code":data.code,
                                                            "policy_type":data.policy_type,
                                                            "value":data.policy_value,
                                                            "company_id":{
                                                                "id":data.company_id.id,
                                                                "name":data.company_id.name
                                                                }
                                                            } for data in env.user.employee_id.loan_policy],
                                            "work_information":{
                                                "job_postion":{
                                                    "id":env.user.employee_id.job_id.id,
                                                    "name":env.user.employee_id.job_id.name
                                                },
                                                "year_of_service":{
                                                    "year":env.user.employee_id.years_of_service,
                                                    "month":env.user.employee_id.months,
                                                    "day":env.user.employee_id.days,
                                                    "classification_id":{
                                                        
                                                        "id":env.user.employee_id.classification_id.id,
                                                        "name":env.user.employee_id.classification_id.name
                                                        },
                                                    "experience_id":{
                                                        "id":env.user.employee_id.experience_id.id,
                                                        "name":env.user.employee_id.experience_id.name,
                                                        
                                                    },
                                                    "grade_id":{
                                                        "id":env.user.employee_id.grade_id.id,
                                                        "name":env.user.employee_id.grade_id.name,
                                                        
                                                    },
                                                    "address_id":{
                                                        "id":env.user.employee_id.address_id.id,
                                                        "name":env.user.employee_id.address_id.name,
                                                        
                                                    },
                                                    "active_location":{
                                                        "id":env.user.employee_id.active_location .id,
                                                        "name":env.user.employee_id.active_location .name,
                                                        
                                                    },
                                                    "location_id":{
                                                        
                                                        "id":env.user.employee_id.location_id.id,
                                                        "name":env.user.employee_id.location_id.name
                                                        
                                                        },
                                                    "province_wage_id":{
                                                        
                                                        "id":env.user.employee_id.province_wage_id.id,
                                                        "name":env.user.employee_id.province_wage_id.name
                                                        
                                                        },
                                                    "resource_calendar_id":{
                                                        
                                                        "id":env.user.employee_id.resource_calendar_id .id,
                                                        "name":env.user.employee_id.resource_calendar_id .name
                                                        
                                                        },
                                                    "timezone":env.user.employee_id.tz
                                                    
                                                    },
                                                "private_information":{
                                                    
                                                    "email":env.user.employee_id.private_email,
                                                    "phone":env.user.employee_id.phone,
                                                    "km_home_work ":env.user.employee_id.km_home_work,
                                                    "religion_id":{
                                                        "id":env.user.employee_id.religion_id.id,
                                                        "name":env.user.employee_id.religion_id.name
                                                        },
                                                    "race_id":{
                                                        "id":env.user.employee_id.race_id.id,
                                                        "name":env.user.employee_id.race_id.name
                                                        },
                                                    "gender":env.user.employee_id.gender,
                                                    "marital_id":{
                                                        "id":env.user.employee_id.marital.id,
                                                        "name":env.user.employee_id.marital.name
                                                        },
                                                    "country_id":{
                                                        "id":env.user.employee_id.country_id.id,
                                                        "name":env.user.employee_id.country_id.name
                                                        },
                                                    "country_domicile_code":{
                                                        "id":env.user.employee_id.country_domicile_code.id,
                                                        "name":env.user.employee_id.country_domicile_code.name
                                                        },
                                                    "state_id ":{
                                                        "id":env.user.employee_id.state_id.id,
                                                        "name":env.user.employee_id.state_id.name
                                                        },
                                                    "identification_id":env.user.employee_id.identification_id,
                                                    "passport_id":env.user.employee_id.passport_id,
                                                    "day":env.user.employee_id.birthday.strftime("%m/%d/%Y") if env.user.employee_id.birthday else "-",
                                                    "place_of_birth":env.user.employee_id.place_of_birth,
                                                    "country_of_birth":{
                                                        "id":env.user.employee_id.country_of_birth.id,
                                                        "name":env.user.employee_id.country_of_birth.name
                                                        
                                                        },
                                                    "age":{
                                                        "birth_years":env.user.employee_id.birth_years,
                                                        "birth_months":env.user.employee_id.birth_months,
                                                        "birth_days":env.user.employee_id.birth_days
                                                        
                                                    }
                                                    
                                                    
                                                },
                                                "medical_information":{
                                                    
                                                    "blood_type":env.user.employee_id.blood_type,
                                                    "height":env.user.employee_id.height,
                                                    "weight":env.user.employee_id.weight
                                                },
                                                "work_permit":{
                                                    "visa_no":env.user.employee_id.visa_no,
                                                    "permit_no":env.user.employee_id.permit_no,
                                                    "visa_expire":env.user.employee_id.visa_expire.strftime("%m/%d/%Y") if env.user.employee_id.visa_expire else "-",
                                                    
                                                    
                                                },
                                                "bpjs_information":{
                                                    "bpjs_ketenagakerjaan_no":env.user.employee_id.bpjs_ketenagakerjaan_no,
                                                    "bpjs_ketenagakerjaan_date":env.user.employee_id.bpjs_ketenagakerjaan_date.strftime("%m/%d/%Y") if env.user.employee_id.bpjs_ketenagakerjaan_date else "-",
                                                    "bpjs_kesehatan_no":env.user.employee_id.bpjs_kesehatan_no,
                                                    "bpjs_kesehatan_date ":env.user.employee_id.bpjs_kesehatan_date.strftime("%m/%d/%Y") if env.user.employee_id.bpjs_kesehatan_date else "-",
                                                    
                                                    
                                                },
                                                "tax_information":{
                                                    "is_expatriate":env.user.employee_id.is_expatriate,
                                                    "have_npwp":env.user.employee_id.have_npwp,
                                                    "npwp_no":env.user.employee_id.npwp_no,
                                                    "employee_tax_category ":env.user.employee_id.employee_tax_category,
                                                    "employee_tax_status":env.user.employee_id.employee_tax_status,
                                                    "tax_calculation_method":env.user.employee_id.tax_calculation_method,
                                                    "ptkp_id":{
                                                        "id":env.user.employee_id.ptkp_id.id,
                                                        "name":env.user.employee_id.ptkp_id.ptkp_name,
                                                        },
                                                    "kpp_id":{
                                                        "id":env.user.employee_id.kpp_id.id,
                                                        "name":env.user.employee_id.kpp_id.name,
                                                        }},
                                                "addresses":[{
                                                            "address_type":data.address_type,
                                                            "street":data.street,
                                                              "location":data.location,
                                                              "country":{
                                                                  "id":data.country_id.id,
                                                                  "name":data.country_id.name,
                                                                  
                                                              },
                                                              "state_id":{
                                                                  "id":data.state_id.id,
                                                                  "name":data.state_id.name
                                                                  
                                                              },
                                                              "postal_code":data.postal_code,
                                                              "tel_number":data.tel_number
                                                              } for data in env.user.employee_id.address_ids],
                                                "emergency":[{"name":data.name,
                                                              "phone":data.phone,
                                                              "relation_id":{
                                                                  "id":data.relation_id.id,
                                                                  "name":data.relation_id.name
                                                                  
                                                              },
                                                              "address":data.address
                                                              } for data in env.user.employee_id.emergency_ids],
                                                "bank":[{"is_used":data.is_used,
                                                              "bank_id":{
                                                                  "id":data.name.id,
                                                                  "name":data.name.name
                                                                  
                                                              },
                                                              "bic":data.bic,
                                                              "unit":data.bank_unit,
                                                              "acc_number":data.acc_number,
                                                              "acc_holder":data.acc_holder,
                                                              } for data in env.user.employee_id.bank_ids],
                                                "dependence_details":[{"name":data.member_name,
                                                              "relation_id":{
                                                                  "id":data.relation_id.id,
                                                                  "name":data.relation_id.name
                                                                  
                                                              },
                                                              "gender":data.gender,
                                                              "age":data.age,
                                                              "education":data.education,
                                                              "occupation":data.occupation,
                                                              "city":data.city
                                                              } for data in env.user.employee_id.fam_ids],
                                                "education_ids":[{"certificate_level":data.certificate,
                                                              "study_field":data.study_field,
                                                              "study_school":data.study_school,
                                                              "city":data.city,
                                                              "graduation_year":data.graduation_year,
                                                              "gpa_score":data.gpa_score
                                                              } for data in env.user.employee_id.education_ids],
                                                
                                                "health_record":[{
                                                            "sequence":data.name,
                                                              "ilness_type":data.illness_type,
                                                              "medical_checkup":data.medical_checkup,
                                                              "date_from":data.date_from.strftime("%m/%d/%Y") if data.date_from else "-",
                                                              "date_to":data.date_to.strftime("%m/%d/%Y") if data.date_to else "-",
                                                              "notes":data.notes,
                                                              
                                                              } for data in env.user.employee_id.health_ids],
                                                "disciplinary_history_ids":[{
                                                            "disciplinary_date":data.dicliplined_date.strftime("%m/%d/%Y") if data.dicliplined_date else "-",
                                                              "disciplinary_stage_id":{
                                                                  "id":data.discliplinary_stage.id,
                                                                  "name":data.discliplinary_stage.disciplinary_name
                                                                  
                                                              },
                                                              "status":data.status,
                                                              "valid_until":data.valid_until.strftime("%m/%d/%Y") if data.valid_until else "-",
                                                              "reason_of_disciplinary":data.reason_of_disciplinary,
                                                              "attachment":data.attachment.decode("utf-8"),
                                                              } for data in env.user.employee_id.disciplinary_stage_ids],
                                                "hr_settings":{
                                                    "status":{
                                                        "user_id":{
                                                            "id":env.user.employee_id.user_id.id,
                                                            "name":env.user.employee_id.user_id.name,
                                                            
                                                            
                                                        },
                                                        "first_contract_date":env.user.employee_id.first_contract_date.strftime("%m/%d/%Y") if env.user.employee_id.first_contract_date else "",
                                                        "leave_struct_id":{
                                                            "id":env.user.employee_id.leave_struct_id.id,
                                                            "name":env.user.employee_id.leave_struct_id.name, 
                                                        }  
                                                    },
                                                    "attendance":{
                                                        "pin_code":env.user.employee_id.pin,
                                                        "barcode":env.user.employee_id.barcode
                                                    },
                                                    "payroll":{
                                                        "payroll_password":env.user.employee_id.payslip_password,
                                                        "analytic_group_id":[{
                                                            "id":data.id,
                                                            "name":data.name, 
                                                        }for data in env.user.employee_id.analytic_group_id]
                                                        
                                                    },
                                                    "timesheets":{
                                                        "timesheet_cost":env.user.employee_id.timesheet_cost
                                                    }
                                                    
                                                },
                                                "checklist":{
                                                    "entry_checklist":{
                                                        "entry_progress":[{"id":data.id,
                                                                          "name":data.name} for data in env.user.employee_id.entry_checklist]
                                                        
                                                    },
                                                    "exit_checklist":{
                                                        "exit_progress":[{"id":data.id,
                                                                          "name":data.name} for data in env.user.employee_id.exit_checklist]
                                                        
                                                    }
                                                    
                                                },
                                                "contract_line_ids":[{"id":data.id,
                                                                      "contract_id":{
                                                                          "id":data.contract_id.id,
                                                                          "name":data.contract_id.name},
                                                                      "job_id":{
                                                                          "id":data.job_id.id,
                                                                          "name":data.job_id.name},
                                                                      "department_id":{
                                                                          "id":data.department_id.id,
                                                                          "name":data.department_id.name},
                                                                      "date_start":data.date_start.strftime("%m/%d/%Y") if data.date_start else "-",
                                                                      "date_end":data.date_end.strftime("%m/%d/%Y") if data.date_end else "-",
                                                                      "wage":data.wage,
                                                                      "rapel_date":data.rapel_date.strftime("%m/%d/%Y") if data.rapel_date else "-",
                                                                      
                                                                      
                                                                      
                                                                      
                                                                      } for data in env.user.employee_id.contract_line_ids],
                                                "transition_line_ids":[{"id":data.id,
                                                                      "emp_transition_id":{
                                                                          "id":data.emp_transition_id.id,
                                                                          "name":data.emp_transition_id.number},
                                                                      "transition_category_id":{
                                                                          "id":data.transition_category_id.id,
                                                                          "name":data.transition_category_id.name},
                                                                      "career_transition_type":{
                                                                          "id":data.career_transition_type.id,
                                                                          "name":data.career_transition_type.name},
                                                                      "transition_date":data.transition_date.strftime("%m/%d/%Y") if data.transition_date else "-",
                                                                      "attachment":data.career_transition_attachment.decode("utf-8") if data.career_transition_attachment else "-",
                                                                      "description":data.description,
                                                                      "company_id":{
                                                                          "id":data.company_id.id,
                                                                          "name":data.company_id.name},
                                                                      } for data in env.user.employee_id.transition_line_ids],
                                                "training_history_ids":[{"id":data.id,
                                                                      "course_id":{
                                                                          "id":data.course_id.id,
                                                                          "name":data.course_id.name},
                                                                      "date_completed":data.date_completed.strftime("%m/%d/%Y") if data.date_completed else "-",
                                                                      "expiry_date":data.expiry_date.strftime("%m/%d/%Y") if data.expiry_date else "-",
                                                                      "attachment":data.certificates.decode("utf-8") if data.certificates else "-",
                                                                      "status":data.state
                                                                      } for data in env.user.employee_id.training_history_ids],
                                                "expense_limit":{
                                                    "expense":[{"id":data.id,
                                                                      "product_id":{
                                                                          "id":data.product_id.id,
                                                                          "name":data.product_id.name},
                                                                      "date_completed":data.limit,
                                                                      
                                                                      } for data in env.user.employee_id.employee_expense_line],
                                                    "cash_advance":{
                                                        "cash_advance_limit":env.user.employee_id.cash_advance_limit
                                                        
                                                        }
                                                    
                                                    
                                                }           
                                            }
                                            }         
                                 )
        
        
    @route(['/api/employee/disciplinary','/api/employee/disciplinary/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_disciplinary(self,id=None,**kw):
        obj = 'hr.employee.disciplinary'
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get('search'):
            domain.append(('disciplinary_number','ilike',kw.get('search')))
            
        hr_employee_disciplinary_ids = request.env[obj].sudo().search(domain)
        if not hr_employee_disciplinary_ids:
            return self.record_not_found()
        
        request_param = {"fields":['status','disciplinary_number','employee_id','discliplinary_stage','dicliplined_date','valid_for_months','valid_until','reason_of_disciplinary','job_position','department_id','company_id','create_uid','create_date']}
        
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in hr_employee_disciplinary_ids),
                             "order":"id desc",
                             "fields":['disciplinary_number','status','employee_id','department_id','dicliplined_date','discliplinary_stage','job_position','valid_until'],
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
           return self.record_not_found()
       
        page_total  = self.get_total_page(len(hr_employee_disciplinary_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                               "page_total":page_total if not id else 0
                                              })
        
    @http.route(['/api/user/job','/api/user/job/<int:id>'],type="http", auth="user",methods=['get'])
    def get_job(self, id= None,**kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'hr.job'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        if kw.get("department_id"):
            print(kw.get("department_id"))
            domain.append(('department_id','in',eval(kw.get("department_id"))))
            
        if kw.get("state"):
            domain.append(('state','in',eval(kw.get("state"))))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['name',
                                    'state',
                                    'company_id',
                                    'classification_id',
                                    'department_id',
                                    'custom_work_location_id',
                                    'website_url',
                                    'skill_ids',
                                    'course_ids',
                                    'e_learning_required_ids',
                                    'no_of_recruitment',
                                    'user_ids',
                                    'create_date',
                                    'create_uid',
                                    'description',
                                    'question_job_position'
                                    ]
                         }
        
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                     'state',
                                                                                     'company_id',
                                                                                     'classification_id',
                                                                                     'department_id',
                                                                                     'custom_work_location_id',
                                                                                     'website_url'
                                                                                     ],
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
        if id:
            if len(response_data[obj]['user_ids']) >= 1:
                response_data[obj]['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],"ids":','.join(str(data) for data in response_data[obj]['user_ids'])},user)
                
            if len(response_data[obj]['skill_ids']) >= 1:
                response_data[obj]['skill_ids'] = self.convert_one2many('hr.skill.type',{"fields":['name'],"ids":','.join(str(data) for data in response_data[obj]['skill_ids'])},user)
                
            if len(response_data[obj]['course_ids']) >= 1:
                response_data[obj]['course_ids'] = self.convert_one2many('training.courses',{"fields":['name'],"ids":','.join(str(data) for data in response_data[obj]['course_ids'])},user)
                
            if len(response_data[obj]['e_learning_required_ids']) >= 1:
                response_data[obj]['e_learning_required_ids'] = self.convert_one2many('slide.channel',{"fields":['name'],"ids":','.join(str(data) for data in response_data[obj]['e_learning_required_ids'])},user)
                
            if len(response_data[obj]['question_job_position']) >= 1:
                response_data[obj]['question_job_position'] = self.convert_one2many('question.job.position',{"fields":['question','modify_question','global_question','mandatory','show_in_job_portal','remarks'],"ids":','.join(str(data) for data in response_data[obj]['question_job_position'])},user)
            
                
        if 'website_url' in response_data[obj]:
            response_data[obj]['website_url'] =  base_url + response_data[obj]['website_url']
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        response =  {"code":200,
                     "data":response_data[obj],
                     "page_total":page_total if not id else 0
                     }
            
        if not id:
            for data_job in response_data[obj]:
                if 'website_url' in data_job:
                    data_job['website_url'] =  base_url + data_job['website_url']
            count_job = request.env[obj].sudo().search_count([])
            response['job_count'] = count_job
                    
        
        return self.get_response(200, '200',response)
        
        


        
        
        
        
        
        
        
        
        
        

