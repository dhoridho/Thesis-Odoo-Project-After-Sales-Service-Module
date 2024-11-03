from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import json
import base64

class Equip3HumanResourceMyPayslips(RestApi):
    @route(['/api/employee/my_payslips/get_payslip_type_list'],auth='user', type='http', methods=['get'])
    def get_payslip_type_list(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.payslip.type'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_ids = request.env[obj].sudo().search([])
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }  
        
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })

    @route(['/api/employee/my_payslips/get_payslip_period_list'],auth='user', type='http', methods=['get'])
    def get_payslip_period_list(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.payslip.period'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('state','=','open')]
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }  
        
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    @route(['/api/employee/my_payslips/get_payslip_period_month_list'],auth='user', type='http', methods=['get'])
    def get_payslip_period_month_list(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.payslip.period.line'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        if not kw.get("period_id"):
            return self.record_not_found()
        domain = [('period_id','=',int(kw.get("period_id"))),('state','=','open')]
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['year','month','start_date','end_date'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }  
        
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })

    @route(['/api/employee/my_payslips'],auth='user', type='json', methods=['POST'])
    def get_my_payslips(self,id=None,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_data = request.jsonrequest
        response = []
        date_from  = datetime.strptime(str(request_data.get('date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('date_to')),"%Y-%m-%d")
        data_create = request.env['hr.my.payslips'].sudo().create({
                                'employee_id':request.env.user.employee_id.id,
                                'payslip_type':request_data.get('payslip_type'),
                                'payslip_period_id':request_data.get('payslip_period_id'),
                                'month':request_data.get('month_id'),
                                'date_from':date_from,
                                'date_to':date_to,
                                })

        domain = [('state', '=', 'done'), ('payslip_pesangon', '=', False)]
        if request.env.user.employee_id:
            domain.append(('employee_id', '=', request.env.user.employee_id.id))
        if data_create.date_from:
            domain.append(('date_from', '=', data_create.date_from))
        if data_create.date_to:
            domain.append(('date_to', '=', data_create.date_to))
        docs = request.env['hr.payslip'].sudo().search(domain, limit=1)
        slip_line = docs.line_ids
        payslip = 0.0
        bonus_payslip = 0.0
        thr_payslip = 0.0
        for line in slip_line:
            for rec in line.salary_rule_id.payslip_type:
                if rec.name == 'Employee Payslip' and rec.id in data_create.payslip_type.ids:
                    payslip += 1.0
                if rec.name == 'Bonus Payslip' and rec.id in data_create.payslip_type.ids:
                    bonus_payslip += 1.0
                if rec.name == 'THR Payslip' and rec.id in data_create.payslip_type.ids:
                    thr_payslip += 1.0
        if payslip == 0 and bonus_payslip == 0 and thr_payslip == 0:
            return self.record_not_found()

        datas = {
            'employee_id': request.env.user.employee_id.id,
            'payslip_type': data_create.payslip_type.ids,
            'month': data_create.month.id,
            'date_from': data_create.date_from,
            'date_to': data_create.date_to,
        }

        pdf = request.env.ref('equip3_hr_payroll_extend_id.action_report_my_payslip')._render_qweb_pdf([data_create.id], data=datas)
        attachment = base64.b64encode(pdf[0]).decode('utf-8')
        attachment_name = "My Payslips " + data_create.month.month + "-" + data_create.month.year
        response.append({
            'attachment_name': attachment_name,
            'attachment': attachment,
        })
        return self.get_response(200, '200', {"code":200,
                                              "data":response
                                              })