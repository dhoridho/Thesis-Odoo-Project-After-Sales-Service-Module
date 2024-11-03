from odoo import http
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta

class OnboardingController(http.Controller):

    @http.route('/approval_dashboard/fetch_dashboard_data', type="json", auth='user')
    def approval_dashboard_fetch_dashboard_data(self):
        obj = request.env['approval.dashboard.report.config']
        configs = obj.sudo().search([])
        chart_data = {'labels':[],'data':[],'labels_pie':[],'origin_label':[]}
        detail_data = []
        my_req_approval = []
        removed_duplicate_my_app = []
        removed_duplicate_my_req = []
        total = 0
        for i in configs:
            state_to_approve = ['to_approve','confirm','confirmed','submit','applied','submitted','selected']

            domain = [(i.approval_field_id.name, '!=', False),
                      (i.approval_state_field_id.name, 'in', ['draft', 'pending', 'Draft', 'Pending']), (
                          i.model_state_id.name, 'in', state_to_approve)]
            rec_count = request.env[i.model_id.model].sudo().search_count(domain)
            total+=rec_count
            rec_datas = request.env[i.model_id.model].sudo().search(domain)
            if rec_count:
                chart_data['origin_label'].append(i.name)
                chart_data['labels'].append(i.name.split(' '))
                chart_data['labels_pie'].append(i.name.replace(' ','\n'))
                
                chart_data['data'].append(int(rec_count))
            if rec_datas:
                for rec in rec_datas:
                    date = rec[i.approval_field_id.name].create_date
                    date =  date + relativedelta(hours=+8)
                    date = datetime.strftime(date, '%d/%m/%Y')
                    current_user = request.env.uid
                    for my_app in rec[i.approval_field_id.name].approvers_ids:
                        approved_user = rec[i.approval_field_id.name].approved_user_ids.ids
                        if my_app.id == current_user and current_user not in approved_user:
                            detail_data.append({
                                'number':rec[i.approval_field_id.name][i.approval_number_field_id.name],
                                'employee':rec[i.approval_field_id.name][i.approval_employee_field_id.name]['name'],
                                'date':date,
                                'id':rec[i.approval_field_id.name].id,
                                'model':i.model_approval_id.model,
                                'name':i.name,
                            })
                    if rec[i.approval_field_id.name].employee_id.user_id.id == current_user:
                        my_req_approval.append({
                            'number':rec[i.approval_field_id.name][i.approval_number_field_id.name],
                            'employee':rec[i.approval_field_id.name][i.approval_employee_field_id.name]['name'],
                            'date':date,
                            'id':rec[i.approval_field_id.name].id,
                            'model':i.model_approval_id.model,
                            'name':i.name,
                        })
        for a in detail_data:
            if a not in removed_duplicate_my_app:
                removed_duplicate_my_app.append(a)
        final_list_my_app = removed_duplicate_my_app
        for b in my_req_approval:
            if b not in removed_duplicate_my_req:
                removed_duplicate_my_req.append(b)
        final_list_my_req = removed_duplicate_my_req
        return {'chart_data': chart_data, 'detail_data': final_list_my_app, 'total': total, 'my_req_approval': final_list_my_req}
