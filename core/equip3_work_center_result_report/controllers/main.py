from odoo import http
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import pytz

class Controller(http.Controller):

    @http.route('/wo_result_report_dashboard/fetch_data', type="json", auth='user')
    def wo_result_report_dashboard_fetch_data(self):
        wo_obj = request.env['mrp.workcenter']
        records_wo = wo_obj.search_read([], fields=["id","name","model"])
        return {'list_wo_n_model': records_wo}




    @http.route('/wo_result_report_dashboard/get_format_table', type="json", auth='user')
    def wo_result_report_dashboard_get_format_table(self, **post):
        wo_obj = request.env['mrp.workcenter']
        consumtion_obj = request.env['mrp.consumption']
        production_obj = request.env['mrp.production']
        employe_obj = request.env['hr.employee']
        format_table = '<br/><br/>'
        wo_id = post['work_center_id']
        period_month = post['period_month'].split('-')
        year = period_month[0]
        month = period_month[1]
        check_calendar = calendar.monthrange(int(year), int(month))
        count_day = check_calendar[1]

        approved_qty = {}
        rejected_qty = {}
        actual_duration = {}
        operators = {}
        target_qty = {}
        efficiency = {}
        expected_duration = {}
        rejected_ratio = {}
        list_lot = {}
        consumption_ids = {}

        for x in range(count_day):
            day = x + 1
            check_date = year+'-'+month+'-'+'{:02d}'.format(day)
            start_date = datetime.strptime(check_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            end_date = datetime.strptime(check_date  + ' 23:59:59', '%Y-%m-%d %H:%M:%S')

            user_tz = pytz.timezone(request.env.user.tz or 'UTC')
            timeoffset = datetime.now(tz=user_tz).strftime('%z')
            timeoffset = int(timeoffset)/100

            start_date = start_date + relativedelta(hours=-timeoffset)
            end_date = end_date + relativedelta(hours=-timeoffset)
      

            basic_consu_domain = [('state','=','confirm'),('create_date','>=',start_date),('create_date','<=',end_date),('workcenter_id','=',wo_id)]
            basic_production_domain = [('state','=','done'),('date_start','>=',start_date),('date_finished','<=',end_date),('consumption_ids.workcenter_id','=',wo_id),('consumption_ids.state','=','confirm')]


            consumtions = consumtion_obj.read_group(basic_consu_domain,['finished_qty:sum'], ['create_date:day'])
            approved_qty[day] = 0
            if consumtions:
                approved_qty[day] = consumtions[0]['finished_qty']


            consumtions = consumtion_obj.read_group(basic_consu_domain,['operator_id'], ['operator_id'])
            operators[day] = ''
            if consumtions:
                for consu in consumtions:
                    if consu['operator_id']:
                        employee = employe_obj.browse(consu['operator_id'][0])
                        operators[day] += employee.name +', '


            consumtions = consumtion_obj.read_group(basic_consu_domain,['rejected_qty:sum'], ['create_date:day'])
            rejected_qty[day] = 0
            if consumtions:
                rejected_qty[day] = consumtions[0]['rejected_qty']


            productions = production_obj.search(basic_production_domain)
            
            actual_duration[day] = 0
            if productions:
                actual_duration[day] = sum(productions.mapped('duration'))

            expected_duration[day] = 0
            if productions:
                expected_duration[day] = sum(productions.mapped('duration_expected'))


            efficiency[day] = 0
            if actual_duration[day]:
                efficiency[day] = round((actual_duration[day]/expected_duration[day]) * 100,2)


            productions = production_obj.read_group(basic_production_domain,['product_qty:sum'], ['state'])
            target_qty[day] = 0
            if productions:
                target_qty[day] = productions[0]['product_qty']


            rejected_ratio[day] = 0
            if rejected_qty[day]:
                rejected_ratio[day] = round((rejected_qty[day]/(rejected_qty[day]+approved_qty[day])) * 100,2)


            productions = production_obj.search(basic_production_domain+[('lot_ids','!=',False)])
            list_lot[day] = ''
            for production in productions:
                for lot in production.lot_ids:
                    if lot.product_id == production.product_id:
                        list_lot[day] += lot.display_name +', '

            consumption_ids[day] = consumtion_obj.search(basic_consu_domain).ids
            

        format_table+='<table class="table">'


        # Header
        format_table+='<tr class="header" style="background-color: rgb(233, 236, 239);">'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2"></td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center" ><div style="font-family: Lato; font-size: 1.08333rem; font-weight: bold; color: rgb(73, 80, 87);">'+str(day)+'</div></td>'
        format_table+='</tr>'


        # TD 1
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1">Shift 1</td><td class="o_sticky_2">Name Operator</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-left"><div>'+str(operators[day])+'</div></td>'
        format_table+='</tr>'


        # TD 2
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2">No Lot</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-left"><div>'+str(list_lot[day])+'</div></td>'
        format_table+='</tr>'


        # TD 2
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2">Operational Time (hours)</td>'
        for x in range(count_day):
            day = x + 1
            hours = round(actual_duration[day] * 180,2)
            format_table+='<td class="text-center"><div>'+str(hours)+'</div></td>'
        format_table+='</tr>'



        # TD 3
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2">Qty Target</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center"><div>'+str(target_qty[day])+'</div></td>'
        format_table+='</tr>'


        # TD 4
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2">Approved Qty</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center"><div>'+str(approved_qty[day])+'</div></td>'
        format_table+='</tr>'


        # TD 5
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2">Rejected Qty</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center"><div>'+str(rejected_qty[day])+'</div></td>'
        format_table+='</tr>'


        # TD 6
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2"> Efficiency (%)</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center"><div>'+str(efficiency[day])+'</div></td>'
        format_table+='</tr>'
        
        
        # TD 7
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2"> Rejected Ratio (%)</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center"><div>'+str(rejected_ratio[day])+'</div></td>'
        format_table+='</tr>'

        # TD 8
        format_table+='<tr>'
        format_table+='<td class="o_set_width o_sticky_1"></td><td class="o_sticky_2"> Remarks</td>'
        for x in range(count_day):
            day = x + 1
            format_table+='<td class="text-center"><div class="button btn btn-primary o_button_remarks" style="font-weight:unset;" data-record_ids="'+str(consumption_ids[day])+'">Remarks</div></td>'
        format_table+='</tr>'


        format_table+='</table>'
        return format_table
