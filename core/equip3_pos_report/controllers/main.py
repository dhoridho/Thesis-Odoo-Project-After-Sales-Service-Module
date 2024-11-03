# -*- coding: utf-8 -*-

import math
import calendar

import datetime as Datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import http
from odoo.http import request
from odoo.http import content_disposition, request, serialize_exception as _serialize_exception

class Home(http.Controller):

    @http.route('/set_attendance_pos', type='json', auth='public')
    def set_attendance_pos(self,pos_id,employee_id):
        pos_branch_id = request.env['pos.config'].browse(int(pos_id)).pos_branch_id.id or False
        history_obj = request.env['pos.login.history'].sudo()
        check_att = history_obj.search([('user_id','=',int(employee_id)),('pos_config_id','=',int(pos_id)),('checkout_datetime','=',False)],limit=1)
        if not check_att:
            history_obj.create({
                'user_id':int(employee_id),
                'pos_config_id':int(pos_id),
                'pos_branch_id':pos_branch_id,
                'checkin_datetime': datetime.now() ,    
            })
            check_att = history_obj.search([('user_id','!=',int(employee_id)),('pos_config_id','=',int(pos_id)),('checkout_datetime','=',False),('checkin_datetime','!=',False)],limit=1)
            if check_att:
                check_att.write({'checkout_datetime':datetime.now()})
        
        return True

    @http.route(['/analytic_pos_dashboard/export'], type='http', auth="public", website=True)
    def analytic_pos_dashboard_export(self, **post):
        csv = "Export Data"
        filename  = "Analytic Dashboard Export"
        return request.make_response(csv,
                            [('Content-Type', 'application/octet-stream'),
                            ('Content-Disposition', content_disposition(filename+'.txt'))])

    @http.route('/analytic_pos_dashboard/fetch_dashboard_data', type="json", auth='user')
    def analytic_pos_dashboard_fetch_dashboard_data(self, company_id, sales_date_compare= False, sales_performance=False, top_10_sort='sfh', 
        topbottom_branch_sort='sfh', topbottom_branch_date=False, top_10_redeem_sort='sa', top_10_plus_sort='sa', promotion_overview_filter='today',
        top10_promotion_filter='s_tpu', promotion_impact_filter1='categories',promotion_impact_filter2='today', select_loyalty_overview='today'):
        company = request.env['res.company'].sudo().browse(int(company_id))

        analytic_data =  {}

        values = self.get_top_10_plus_point(top_10_plus_sort)
        analytic_data['top_10_plus_sort'] = values['plus_sort']
        analytic_data['chart_Top_10_PP_array_data'] = values['chart_data']
        analytic_data['chart_Top_10_PP_label'] = values['chart_label']

        values = self.get_top_10_redeem_point(top_10_redeem_sort)
        analytic_data['top_10_redeem_sort'] = values['redeem_sort']
        analytic_data['chart_Top_10_PR_array_data'] = values['chart_data']
        analytic_data['chart_Top_10_PR_label'] = values['chart_label']

        values = self.get_promotion_impact(promotion_impact_filter1, promotion_impact_filter2)
        analytic_data['promotion_impact_filter1'] = values['filter1']
        analytic_data['promotion_impact_filter2'] = values['filter2']
        analytic_data['promotion_impact_sales_volume_chart'] = values['sales_volume_chart']
        analytic_data['promotion_impact_chart_labels'] = values['chart_labels']
        analytic_data['promotion_impact_uplift_sales_volume_chart'] = values['uplift_sales_volume_chart']
        analytic_data['promotion_impact_uplift_sales_volume_labels'] = values['uplift_sales_volume_labels']
        analytic_data['promotion_impact_uplift_sales_volume_chart_BC'] = values['uplift_sales_volume_chart_BC']

        values = self.get_promotion_overview(company, promotion_overview_filter)
        analytic_data['promotion_overview_filter'] = values['promotion_overview_filter']
        analytic_data['promotion_overview_ongoing'] = values['promotion_overview_ongoing']
        analytic_data['promotion_overview_using'] = values['promotion_overview_using']
        analytic_data['promotion_overview_percentage'] = values['promotion_overview_percentage']

        values = self.get_loyalty_overview(select_loyalty_overview)
        analytic_data['ongoing_loyalty'] = values['ongoing_loyalty']
        analytic_data['repeat_customer_rate'] = values['repeat_customer_rate']
        analytic_data['new_member'] = values['new_member']
        analytic_data['total_redeem'] = values['total_redeem']
        analytic_data['select_loyalty_overview'] = values['select_loyalty_overview']
        
        values = self.get_table_of_branch_sales()
        analytic_data['table_arr_branch_sales'] = values['data']

        values = self.get_top_10_product(top_10_sort)
        analytic_data['top_10_sort'] = values['top_10_sort']
        analytic_data['chart_Top_10_p'] = values['chart_Top_10_p']

        values = self.get_total_categories_sold()
        analytic_data['chartTopCategSold'] = values['chartTopCategSold']
        analytic_data['chartTopCategSoldColor'] = values['chartTopCategSoldColor']
        analytic_data['chartTopCategSoldParent'] = values['chartTopCategSoldParent']

        values = self.get_top_bottom_branch(topbottom_branch_sort, topbottom_branch_date)
        analytic_data['topbottom_branch_sort'] = values['topbottom_branch_sort']
        analytic_data['topbottom_branch_date'] = values['topbottom_branch_date']
        analytic_data['chartTopBottomBranch'] = values['chartTopBottomBranch']
        analytic_data['chartTopBottomBranchcolor'] = values['chartTopBottomBranchcolor']

        values = self.sales_overview(company, sales_date_compare=sales_date_compare)
        analytic_data['total_sales_curr'] = values['total_sales_curr']
        analytic_data['total_transaction'] = values['total_transaction']
        analytic_data['avg_transaction_curr'] = values['avg_transaction_curr']

        analytic_data['sales_compare'] = values['sales_compare']
        analytic_data['sales_date_compare'] = values['sales_date_compare']
        analytic_data['percentage_total_sales_positive'] = values['percentage_total_sales_positive']
        analytic_data['percentage_total_transaction_positive'] = values['percentage_total_transaction_positive']
        analytic_data['percentage_avg_sales_positive'] = values['percentage_avg_sales_positive']
        analytic_data['percentage_total_sales_str'] = values['percentage_total_sales_str']
        analytic_data['percentage_total_transaction_str'] = values['percentage_total_transaction_str']
        analytic_data['percentage_avg_sales_str'] = values['percentage_avg_sales_str']

        values = self.get_actions()
        analytic_data['action_sale_dashboard'] = values['action_sale_dashboard']
        analytic_data['action_promotion_dashboard'] = values['action_promotion_dashboard']
        analytic_data['action_loyalties_dashboard'] = values['action_loyalties_dashboard']

        values = self.get_sales_performance(sales_performance)
        analytic_data['chart_SP'] = values['chart_SP']
        analytic_data['sales_performance'] = values['sales_performance']

        values = self.get_top10_promotion(top10_promotion_filter)
        analytic_data['top10_promotion_filter'] = values['promotion_filter']
        analytic_data['top10_promotion_chart_labels'] = values['chart_labels']
        analytic_data['top10_promotion_chart_data'] = values['chart_data']

        values = self.get_chart_TaCR_vals()
        analytic_data['chart_TaCR'] = values['chart_TaCR']

        return analytic_data

    def get_top_10_plus_point(self, plus_sort):
        request._cr.execute('''
            SELECT 
                plp.loyalty_rule_id,
                plr.name,
                SUM(plp.point)
            FROM pos_loyalty_point AS plp 
            INNER JOIN pos_loyalty_rule AS plr ON (plp.loyalty_rule_id = plr.id)
            WHERE plp.state = 'ready' 
                AND plp.type IN ('plus','import')
            GROUP BY plr.name, plp.loyalty_rule_id 
            ORDER BY SUM(plp.point) 
            DESC 
            LIMIT 10 ;
        ''')
        results = request._cr.fetchall()
        results = { x[1]: x[2] for x in results}
 
        chart_label = []
        chart_data = []
        chart_point_data = []
        if results:
            if plus_sort == 'sa':
                myKeys = list(results.keys())
                myKeys.sort()
                results = {i: results[i] for i in myKeys}
            elif plus_sort == 'sfl':
                results = sorted(results.items(), key=lambda x:x[1])
            elif plus_sort == 'sfh':
                results = sorted(results.items(), key=lambda x:x[1], reverse=True)

            if plus_sort != 'sa':
                for i in results:
                    chart_label.append(i[0])
                    chart_point_data.append(i[1])
            else:
                for i in results:
                    chart_label.append(i)
                    chart_point_data.append(results[i])

            chart_data.append({
               'label': 'Total Points',
               'data': chart_point_data,
               'backgroundColor':'#6EC3C3',
            })

        values = {
            'plus_sort': plus_sort,
            'chart_data': chart_data,
            'chart_label': chart_label,
        }
        return values

    def get_top_10_redeem_point(self, redeem_sort):
        request._cr.execute('''
            SELECT 
                plp.loyalty_reward_id,
                plr.name,
                SUM(plp.point)
            FROM pos_loyalty_point AS plp 
            INNER JOIN pos_loyalty_reward AS plr ON (plp.loyalty_reward_id=plr.id)
            where plp.state = 'ready' 
                AND plp.type = 'redeem'
            GROUP BY plr.name, plp.loyalty_reward_id 
            ORDER BY SUM(plp.point) DESC 
            LIMIT 10 ;
        ''')
        results = request._cr.fetchall()
        results = { x[1]: x[2] for x in results}
        
        chart_label = []
        chart_data = []
        chart_point_data = []
        if results:
            if redeem_sort == 'sa':
                myKeys = list(results.keys())
                myKeys.sort()
                results = {i: results[i] for i in myKeys}
            elif redeem_sort == 'sfl':
                results = sorted(results.items(), key=lambda x:x[1])
            elif redeem_sort == 'sfh':
                results = sorted(results.items(), key=lambda x:x[1], reverse=True)

            if redeem_sort != 'sa':
                for i in results:
                    chart_label.append(i[0])
                    chart_point_data.append(i[1])
            else:
                for i in results:
                    chart_label.append(i)
                    chart_point_data.append(results[i])
                
            chart_data.append({
               'label': 'Total Points',
               'data': chart_point_data,
               'backgroundColor':'#8E6EC3',
            })

        values = {
            'redeem_sort': redeem_sort,
            'chart_data': chart_data,
            'chart_label': chart_label
        }
        return values

    def get_promotion_impact_qty_by_product_id(self, start_date, end_date):
        qty_by_product_id = {}
        request._cr.execute('''
            SELECT 
                pol.product_id,
                SUM(pol.qty)
            FROM pos_order_line AS pol
            INNER JOIN pos_order po ON po.id = pol.order_id
            WHERE pol.product_id IS NOT NULL
                AND pol.product_id IS NOT NULL
                AND pol.promotion_id IS NOT NULL
                AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}') 
            GROUP BY pol.product_id
        '''.format(start_date=start_date, end_date=end_date))
        results = request._cr.fetchall()
        for result in results:
            qty_by_product_id[result[0]] = result[1]
        return qty_by_product_id

    def get_promotion_impact_qty_by_categ_id(self, start_date, end_date):
        qty_by_categ_id = {}

        request._cr.execute('''
            SELECT 
                id,
                SUM(total_qty) AS total_qty
            FROM (
                SELECT 
                    cat.id, 
                    SUM(l.qty) AS total_qty
                FROM pos_order_line AS l
                INNER JOIN pos_order AS po ON po.id = l.order_id
                INNER JOIN product_product AS pp ON pp.id = l.product_id
                INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                INNER JOIN pos_category AS cat ON cat.id = pt.pos_categ_id
                WHERE l.promotion_id IS NOT NULL
                    AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}') 
                GROUP BY cat.id

                UNION

                 -- Start: Section if Product has multi category
                SELECT 
                    cat.id,
                    SUM(l.qty) AS total_qty
                FROM pos_order_line AS l
                INNER JOIN pos_order AS po ON po.id = l.order_id
                INNER JOIN product_product AS pp ON pp.id = l.product_id
                INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                INNER JOIN pos_category_product_template_rel AS pcpt_rel ON pcpt_rel.product_template_id = pt.id
                INNER JOIN pos_category AS cat ON cat.id = pcpt_rel.pos_category_id
                    AND pt.multi_category = 't'
                WHERE l.promotion_id IS NOT NULL
                    AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}') 
                GROUP BY cat.id 
                -- End: Section if Product has multi category
                  ) AS t
            GROUP BY 
                id
            ORDER BY total_qty DESC
        '''.format(start_date=start_date, end_date=end_date))
        results = request._cr.fetchall()
        for result in results:
            qty_by_categ_id[result[0]] = result[1]
        return qty_by_categ_id

    def get_promotion_impact(self, filter1, filter2):
        now = datetime.now()

        if filter2 == 'tw':
            first_date_week = now - relativedelta(days=now.weekday())
            first_date_week_before = first_date_week - relativedelta(days=7)
            end_date_week_before = first_date_week_before + relativedelta(days=6)
            uplift_datetime_start = first_date_week_before.strftime('%Y-%m-%d 00:00:00') 
            uplift_datetime_end = end_date_week_before.strftime('%Y-%m-%d 23:59:59') 

            datetime_start = first_date_week.strftime('%Y-%m-%d 00:00:00') 
            datetime_end = now.strftime('%Y-%m-%d 23:59:59') 

        elif filter2 == 'tm':
            last_date_month = str(calendar.monthrange(int(now.strftime('%Y')), int(now.strftime('%m')))[1])
            uplift_datetime_start = now.strftime('%Y-%m-01 00:00:00') 
            uplift_datetime_end = now.strftime('%Y-%m-'+last_date_month+' 23:59:59') 
            uplift_datetime_start = ( datetime.strptime(uplift_datetime_start,'%Y-%m-%d %H:%M:%S') - relativedelta(months=1) ).strftime('%Y-%m-%d %H:%M:%S')
            uplift_datetime_end = ( datetime.strptime(uplift_datetime_end,'%Y-%m-%d %H:%M:%S') - relativedelta(months=1) ).strftime('%Y-%m-%d %H:%M:%S')

            datetime_start = now.strftime('%Y-%m-01 00:00:00') 
            datetime_end = now.strftime('%Y-%m-'+last_date_month+' 23:59:59') 

        elif filter2 == 'ty':
            uplift_datetime_start = now.strftime('%Y-01-01 00:00:00') 
            uplift_datetime_end = now.strftime('%Y-12-31 23:59:59') 
            uplift_datetime_start = ( datetime.strptime(uplift_datetime_start,'%Y-%m-%d %H:%M:%S')  - relativedelta(years=1) ).strftime('%Y-%m-%d %H:%M:%S')
            uplift_datetime_end = ( datetime.strptime(uplift_datetime_end,'%Y-%m-%d %H:%M:%S') - relativedelta(years=1) ).strftime('%Y-%m-%d %H:%M:%S')

            datetime_start = now.strftime('%Y-01-01 00:00:00') 
            datetime_end = now.strftime('%Y-12-31 23:59:59') 
        
        else:
            uplift_datetime_start = now.strftime('%Y-%m-%d 00:00:00') 
            uplift_datetime_end = now.strftime('%Y-%m-%d 23:59:59') 
            uplift_datetime_start = ( datetime.strptime(uplift_datetime_start,'%Y-%m-%d %H:%M:%S') - relativedelta(days=1) ).strftime('%Y-%m-%d %H:%M:%S')
            uplift_datetime_end = ( datetime.strptime(uplift_datetime_end,'%Y-%m-%d %H:%M:%S') - relativedelta(days=1) ).strftime('%Y-%m-%d %H:%M:%S')

            datetime_start = now.strftime('%Y-%m-%d 00:00:00') 
            datetime_end = now.strftime('%Y-%m-%d 23:59:59')


        data_data = {}
        uplift_impact_data = {}
        product_name_by_id = {}
        categ_name_by_id = {}
        if filter1 == 'products':
            data_data = self.get_promotion_impact_qty_by_product_id(datetime_start, datetime_end)
            uplift_impact_data = self.get_promotion_impact_qty_by_product_id(uplift_datetime_start, uplift_datetime_end)
            product_ids = list(set([x for x in data_data] + [x for x in uplift_impact_data]))
            products = request.env['product.product'].sudo().with_context(active_test=False).search_read([('id','in',product_ids)], ['id','name'])
            for product in products:
                product_name_by_id[product['id']] = product['name']
        else:
            data_data = self.get_promotion_impact_qty_by_categ_id(datetime_start, datetime_end)
            uplift_impact_data = self.get_promotion_impact_qty_by_categ_id(uplift_datetime_start, uplift_datetime_end)
            categ_ids = list(set([x for x in data_data] + [x for x in uplift_impact_data]))
            categs = request.env['pos.category'].sudo().with_context(active_test=False).search_read([('id','in',categ_ids)], ['id','name'])
            for categ in categs:
                categ_name_by_id[categ['id']] = categ['name']

        chart_labels = []
        sales_volume_chart_data = []
        uplift_chart_labels = []
        uplift_sales_volume_chart_data = []

        uplift_sales_volume_labels = []
        uplift_sales_volume_chart_BC = []
        for res_id in data_data:
            if filter1 == 'products':
                chart_labels.append(product_name_by_id[res_id])
                uplift_sales_volume_labels.append(product_name_by_id[res_id])
            else:
                chart_labels.append(categ_name_by_id[res_id])
                uplift_sales_volume_labels.append(categ_name_by_id[res_id])

            total_qty = data_data[res_id]
            sales_volume_chart_data.append(total_qty)

            r = total_qty - (uplift_impact_data.get(res_id) or 0)
            if r >= 0:
                uplift_sales_volume_chart_BC.append('#2C84C7')
            else:
                uplift_sales_volume_chart_BC.append('red')
            uplift_sales_volume_chart_data.append(r)

        sales_volume_chart = [{
           'label': 'Qty',
           'data': sales_volume_chart_data,
           'backgroundColor':'#2C84C7',
        }]

        uplift_sales_volume_chart = [{
           'label': 'Qty',
           'data': uplift_sales_volume_chart_data,
           #'backgroundColor': '#2C84C7',
        }]

        values = {
            'filter1': filter1,
            'filter2': filter2,

            'sales_volume_chart': sales_volume_chart,
            'chart_labels': chart_labels,
            'uplift_sales_volume_chart': uplift_sales_volume_chart,
            'uplift_sales_volume_labels': uplift_sales_volume_labels,
            'uplift_sales_volume_chart_BC': uplift_sales_volume_chart_BC,
        }
        return values

    def get_promotion_overview(self,company, promotion_overview_filter):
        Monetary = request.env['ir.qweb.field.monetary']
        now = datetime.now()
        
        if promotion_overview_filter == 'tw':
            first_date_week = now - relativedelta(days=now.weekday())
            start_date = first_date_week.strftime('%Y-%m-%d 00:00:00')
            end_date = now.strftime('%Y-%m-%d 23:59:59')
        elif promotion_overview_filter == 'tm':
            last_date_month = str(calendar.monthrange(int(now.strftime('%Y')), int(now.strftime('%m')))[1])
            start_date = now.strftime('%Y-%m-01 00:00:00')
            end_date = now.strftime('%Y-%m-'+last_date_month+' 23:59:59')
        elif promotion_overview_filter == 'ty':
            start_date = now.strftime('%Y-01-01 00:00:00')
            end_date = now.strftime('%Y-12-31 23:59:59')
        else:
            start_date = now.strftime('%Y-%m-%d 00:00:00')
            end_date = now.strftime('%Y-%m-%d 23:59:59')

        domain = [('state','=','active'),('start_date','>=',start_date),('end_date','<=',end_date)]
        promotion_ongoing_count = request.env['pos.promotion'].sudo().search_count(domain)

        request._cr.execute('''
            SELECT 
                COUNT(pol.id),
                COALESCE(SUM(pol.price_subtotal_incl), 0)
            FROM pos_order_line AS pol
            INNER JOIN pos_order po ON po.id = pol.order_id
            WHERE pol.product_id IS NOT NULL
                AND pol.promotion_id IS NOT NULL
                AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}') 
        '''.format(start_date=start_date, end_date=end_date))
        result = request._cr.fetchall()
        promotion_using_count = result[0][0]
        promotion_using_total = result[0][1]

        promotion_percentage = 0
        if promotion_using_count:
            if promotion_using_count and not promotion_using_total:
                promotion_percentage = 100
            promotion_percentage = math.ceil((promotion_using_count/promotion_using_total) * 100)

        promotion_using = Monetary.value_to_html(promotion_using_total, {'display_currency': company.currency_id})
        promotion_using = promotion_using.replace("oe_currency_value","")
        promotion_using = promotion_using.replace('<span class="">',"")
        promotion_using = promotion_using.replace("</span>","") 


        values = {
            'promotion_overview_filter': promotion_overview_filter,
            'promotion_overview_ongoing': promotion_ongoing_count,
            'promotion_overview_using': promotion_using,
            'promotion_overview_percentage': promotion_percentage,
        }
        return values


    def get_loyalty_overview(self, select_loyalty_overview):
        now = datetime.now()
        if select_loyalty_overview == 'tw':
            first_date_week = now - relativedelta(days = now.weekday())
            start_date = first_date_week.strftime('%Y-%m-%d 00:00:00') 
            end_date = now.strftime('%Y-%m-%d 23:59:59') 
        elif select_loyalty_overview == 'tm':
            last_date_month = str(calendar.monthrange(int(now.strftime('%Y')), int(now.strftime('%m')))[1])
            start_date = now.strftime('%Y-%m-01 00:00:00') 
            end_date = now.strftime('%Y-%m-'+last_date_month+' 23:59:59') 
        elif select_loyalty_overview == 'ty':
            start_date = now.strftime('%Y-01-01 00:00:00') 
            end_date = now.strftime('%Y-12-31 23:59:59') 
        else:
            start_date = now.strftime('%Y-%m-%d 00:00:00') 
            end_date = now.strftime('%Y-%m-%d 23:59:59') 

        domain = [('state','=','running'),('start_date','>=',start_date),'|',('end_date','<=',end_date),('end_date','=',False)]
        ongoing_loyalty = request.env['pos.loyalty'].sudo().search_count(domain)

        domain = [('is_pos_member','=',True),('create_date','>=',start_date),('create_date','<=',end_date)]
        new_member = request.env['res.partner'].sudo().search_count(domain)

        domain = [('type','=','redeem'),('state','=','ready'),('create_date','>=',start_date),('create_date','<=',end_date)]
        total_redeem = sum(request.env['pos.loyalty.point'].sudo().search(domain).mapped('point'))
        total_redeem = total_redeem and (total_redeem.is_integer() and int(total_redeem) or ('{:,.0f}'.format(total_redeem))) or 0

        request._cr.execute('''
            SELECT t.partner_id, t.order_count
            FROM (
                SELECT 
                    partner_id, 
                    COUNT(id) AS order_count
                FROM pos_order
                WHERE partner_id IS NOT NULL
                    AND state NOT IN ('draft', 'cancel', 'quotation')
                    AND (date_order >= '{start_date}' AND date_order <= '{end_date}') 
                GROUP by partner_id
            ) t
            WHERE t.order_count > 1
        '''.format(start_date=start_date, end_date=end_date))
        repeat_customer_rate = len(request._cr.fetchall())
                    
        
        values = {
            'ongoing_loyalty': ongoing_loyalty,
            'repeat_customer_rate': repeat_customer_rate,
            'new_member': new_member,
            'total_redeem': total_redeem,
            'select_loyalty_overview': select_loyalty_overview,
        }
        return values

    def branch_sales_query(self, start_date, end_date):
        result_by_branch_id = {}
        query = '''
           SELECT 
                po.pos_branch_id,
                SUM(po.amount_total) AS total_sale,
                COUNT(po.id) AS total_transaction
            FROM pos_order AS po
            WHERE po.state NOT IN ('draft', 'cancel', 'quotation')
                AND po.pos_branch_id IS NOT NULL
                AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}') 
            GROUP BY po.pos_branch_id
        '''.format(start_date=start_date, end_date=end_date)
        request._cr.execute(query)
        results = request._cr.fetchall()
        for result in results:
            result_by_branch_id[result[0]] = {
                'total_sale': result[1],
                'total_transaction': result[2],
            }
        return result_by_branch_id


    def get_branch_sales_cogs_by_branch_id(self, start_date, end_date):
        standard_price_by_product_id = {}

        query = '''
            SELECT
                po.pos_branch_id,
                pol.product_id, 
                SUM(pol.qty)
            FROM pos_order_line as pol 
            INNER JOIN pos_order po ON po.id = pol.order_id
            INNER JOIN product_product pp ON pp.id = pol.product_id
            WHERE po.state NOT IN ('draft', 'cancel', 'quotation')
                AND po.pos_branch_id IS NOT NULL
                AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}') 
            GROUP BY po.pos_branch_id, pol.product_id
        '''.format(start_date=start_date, end_date=end_date)
        request._cr.execute(query)
        results = request._cr.fetchall()

        product_ids = list(set([ x[1] for  x in results]))
        products = request.env['product.product'].sudo().with_context(active_test=False).search_read([('id','in',product_ids)], ['id', 'standard_price'])
        for product in products:
            standard_price_by_product_id[product['id']] = product['standard_price']

        cogs_by_branch_id = {}
        for result in results:
            pos_branch_id = int(result[0])
            product_id = result[1]
            total_qty = result[2]

            cost_of_good_sold = total_qty * standard_price_by_product_id.get(product_id, 0)

            if pos_branch_id in cogs_by_branch_id:
                cogs_by_branch_id[pos_branch_id] = (cogs_by_branch_id[pos_branch_id] + cost_of_good_sold)
            else:
                cogs_by_branch_id[pos_branch_id] = cost_of_good_sold

        return cogs_by_branch_id


    def get_table_of_branch_sales(self):
        data = []
        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')

        yesterday_start_date = (datetime.now() - relativedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
        yesterday_end_date = (datetime.now() - relativedelta(days=1)).strftime('%Y-%m-%d 23:59:59')

        branchs = request.env['res.branch'].sudo().search_read([], ['id', 'name'])

        sales_by_branch_id = self.branch_sales_query(start_date, end_date)
        ystd_sales_by_branch_id = self.branch_sales_query(yesterday_start_date, yesterday_end_date)
        cogs_by_branch_id = self.get_branch_sales_cogs_by_branch_id(start_date, end_date)


        for branch in branchs:
            branch_id = branch['id']
            branch_name = branch['name']

            sales = sales_by_branch_id.get(branch_id)
            total_sale = sales and sales['total_sale'] or 0
            total_transaction = sales and sales['total_transaction'] or 0
            avg_transaction = total_sale and total_transaction and (total_sale / total_transaction) or 0

            ystd_sales = ystd_sales_by_branch_id.get(branch_id)
            ystd_total_sale = ystd_sales and ystd_sales['total_sale'] or 0
            ystd_total_transaction = ystd_sales and ystd_sales['total_transaction'] or 0
            ystd_avg_transaction = ystd_total_sale and ystd_total_transaction and (ystd_total_sale / ystd_total_transaction) or 0

            revenue = total_sale - cogs_by_branch_id.get(branch_id, 0)

            performance = 0
            different = total_sale - ystd_total_sale
            if different > 0:
                if ystd_total_sale:
                    performance = int(round((different/(ystd_total_sale))*100,0))
            elif different < 0:
                if total_sale:
                    performance = int(round((different/total_sale)*100,0))
                else:
                    performance = -100
            else:
                performance = 0


            _color = performance > 0 and 'green' or 'red'
            _total_sale = '{:,.0f}'.format(total_sale)
            _total_transaction = '{:,.0f}'.format(total_transaction)
            _avg_transaction = '{:,.0f}'.format(avg_transaction)
            _revenue = '{:,.0f}'.format(revenue)
            _performance = f'{performance}%'

            data.append([
                branch_name,
                _total_sale,
                _total_transaction,
                _avg_transaction,
                _revenue,
                _performance,
                _color
            ])


        values = {
            'data': data
        }
        return values

    def get_top_10_product(self, top_10_sort='sfh'):
        data = []
        labels = []
        array_data = []

        index_product_id = 0
        index_product_name = 1
        index_total_qty = 2
        request._cr.execute('''
            SELECT 
                pol.product_id, 
                pt.name,
                SUM(pol.qty)
            FROM pos_order_line as pol 
            INNER JOIN pos_order po ON po.id = pol.order_id
            INNER JOIN product_product pp ON pp.id = pol.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE po.state NOT IN ('draft', 'cancel', 'quotation') 
            GROUP BY pol.product_id, pt.name 
            ORDER BY SUM(pol.qty) DESC 
            LIMIT 10 
        ''')
        results = request._cr.fetchall()

        for result in results:
            if top_10_sort == 'sfh':
                data.append(result[index_total_qty])
                labels.append(result[index_product_name])
            else:
                data.insert(0, result[index_total_qty])
                labels.insert(0, result[index_product_name])

        array_data.append({
           'label': 'Total Qty',
           'data': data,
           'backgroundColor':'#24AED9',
        })

        chart_Top_10_p = {
            'labels': labels,
            'array_data': array_data,
        }
        values = {
            'top_10_sort': top_10_sort,
            'chart_Top_10_p': chart_Top_10_p,
        }
        return values

    def get_total_categories_sold(self):
        categtopcolor = ['#E67C73','#F7CB4D','#41B375','#7BAAF7','#BA67C8']
        chartTopCategSold = []

        request._cr.execute('''
            SELECT 
                id,
                name,
                parent_id, 
                array_agg(all_childs) AS all_childs,
                SUM(total_qty) AS total_qty
            FROM (

                SELECT 
                    cat.id, 
                    cat.name,
                    cat.parent_id,
                    null AS all_childs,
                    SUM(l.qty) AS total_qty
                FROM pos_order_line AS l
                INNER JOIN pos_order AS po ON po.id = l.order_id
                INNER JOIN product_product AS pp ON pp.id = l.product_id
                INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                INNER JOIN pos_category AS cat ON cat.id = pt.pos_categ_id
                WHERE po.state NOT IN ('draft', 'cancel', 'quotation')
                GROUP BY
                    cat.id, 
                    cat.name,
                    cat.parent_id

                UNION

                -- Start: Section if Product has multi category
                SELECT 
                    cat.id, 
                    cat.name,
                    cat.parent_id,
                    null AS all_childs,
                    SUM(l.qty) AS total_qty
                FROM pos_order_line AS l
                INNER JOIN pos_order AS po ON po.id = l.order_id
                INNER JOIN product_product AS pp ON pp.id = l.product_id
                INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                INNER JOIN pos_category_product_template_rel AS pcpt_rel ON pcpt_rel.product_template_id = pt.id
                INNER JOIN pos_category AS cat ON cat.id = pcpt_rel.pos_category_id
                WHERE po.state NOT IN ('draft', 'cancel', 'quotation')
                    AND pt.multi_category = 't'
                GROUP BY
                    cat.id, 
                    cat.name,
                    cat.parent_id
                -- End: Section if Product has multi category

                UNION

                -- Start: Section for select all category and get all childs
                SELECT 
                    cat.id, 
                    cat.name,
                    cat.parent_id,
                    (
                        with RECURSIVE cte as 
                        (
                          SELECT rc_cat1.id FROM pos_category rc_cat1 WHERE rc_cat1.id=cat.id
                          UNION ALL
                          SELECT rc_cat2.id FROM pos_category rc_cat2 INNER JOIN cte ON rc_cat2.parent_id=cte.id
                        )
                        SELECT array_to_string(ARRAY_AGG(id), ',') FROM cte -- get all children ids that belong to this category
                    ) AS all_childs,
                    0 AS total_qty
                FROM pos_category AS cat
                -- End: Section for select all category and get all childs

            ) AS t
            GROUP BY 
                id,
                name,
                parent_id
            ORDER BY total_qty DESC
        ''')
        results = request._cr.fetchall()
        index_id = 0
        index_name = 1
        index_parent_id = 2
        index_all_childs = 3
        index_total_qty = 4

        qty_by_categ_id = {x[index_id]: x[index_total_qty] for x in results}
        for result in results:
            _total_qty = result[index_total_qty]
            _id = result[index_id]

            all_child_ids = []
            for _val in result[index_all_childs]:
                if _val != None:
                    all_child_ids += [int(x) for x in _val.split(',')]
            all_child_ids = list(set(all_child_ids))

            for child_id in all_child_ids:
                if child_id != _id:
                    _total_qty += qty_by_categ_id.get(child_id, 0)
            qty_by_categ_id[_id] = _total_qty

        display_name_by_categ_id = {}
        categs = request.env['pos.category'].sudo().search_read([], ['display_name'])
        for categ in categs:
            display_name_by_categ_id[categ['id']] = categ['display_name']


        all_categories_by_id = {}
        for result in results:
            _id = result[index_id]
            all_child_ids = []
            for _val in result[index_all_childs]:
                if _val != None:
                    all_child_ids += [int(x) for x in _val.split(',')]
            all_child_ids = list(set(all_child_ids))

            categ_values = {
                'id': _id,
                'name': display_name_by_categ_id[_id],
                'parent_id': result[index_parent_id],
                'Total Qty': qty_by_categ_id.get(_id, 0),
                'all_child_ids': all_child_ids,
                'all_childs': [],
                'color': '#d5d5d5'
            }
            all_categories_by_id[_id] = categ_values

        for categ_id in all_categories_by_id:
            for child_id in all_categories_by_id[categ_id]['all_child_ids']:
                if child_id != categ_id:
                    all_categories_by_id[categ_id]['all_childs'].append(all_categories_by_id[child_id])


        all_categories = [ all_categories_by_id[categ_id] for categ_id in all_categories_by_id ]
        all_categories = sorted(all_categories, key=lambda d: d['Total Qty'], reverse=True)

        categ_wo_parent = list(filter(lambda d: d['parent_id'] == None, all_categories))
        categ_wo_parent = categ_wo_parent[:len(categtopcolor)] # limit Parent Category by colors

        for index, categ in enumerate(categ_wo_parent):
            color = categtopcolor[index]
            chartTopCategSold += [{
                'id': categ['id'],
                'name': categ['name'],
                'parent_id': categ['parent_id'],
                'Total Qty': categ['Total Qty'],
                'color': color,
            }]
            all_childs = categ['all_childs'][:10] # limit only 10 childs
            for child in all_childs:
                chartTopCategSold += [{
                    'id': child['id'],
                    'name': child['name'],
                    'parent_id': child['parent_id'],
                    'Total Qty': child['Total Qty'],
                    'color': color,
                }]

        values = {
            'chartTopCategSold': chartTopCategSold,
            'chartTopCategSoldColor': categtopcolor,
            'chartTopCategSoldParent': [],
        } 
        return values



    def get_top_bottom_branch(self, topbottom_branch_sort='sfh', topbottom_branch_date=False):
        arr_chart_topbottom_branch = []
        labels = []
        chartTopBottomBranchColor = [] 

        topbottom_branch_date = not topbottom_branch_date and datetime.now().strftime("%d/%m/%Y") or topbottom_branch_date # Date from local client
        start_date = datetime.strptime(topbottom_branch_date + ' 00:00:00','%d/%m/%Y %H:%M:%S')
        end_date = datetime.strptime(topbottom_branch_date + ' 23:59:59','%d/%m/%Y %H:%M:%S')

        request._cr.execute(f'''
            SELECT 
                po.pos_branch_id, 
                rb.name,
                SUM(amount_total), -- total sale
                COUNT(po.id) -- total transaction
            FROM pos_order AS po
            LEFT JOIN res_branch AS rb ON rb.id = po.pos_branch_id
            WHERE po.state NOT IN ('draft', 'cancel', 'quotation')
                AND po.pos_branch_id IS NOT NULL
                AND (date_order >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND date_order <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}')
            GROUP BY po.pos_branch_id, rb.name
        ''')
        results = request._cr.fetchall()

        branch_name_index = 1
        total_sale_index = 2
        total_transaction_index = 3

        if topbottom_branch_sort in ['sfh', 'sfl']:
            from_top_data = sorted(results, key=lambda x:x[total_sale_index], reverse=True) # by total sale
            from_top_data = from_top_data[:5] # limit to 5 result

            from_bottom_data = sorted(results, key=lambda x:x[total_sale_index])  # by total sale
            from_bottom_data = from_bottom_data[:5] # limit to 5 result

            if topbottom_branch_sort == 'sfh': # Sort From Highest (Total Sale)
                data = []
                for tatb in from_top_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_sale_index])
                    chartTopBottomBranchColor.append('#BC5090')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Sales Top Branch',
                   'data': data,
                   'backgroundColor':'#BC5090',
                })

                data = []
                for tatb in from_bottom_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_sale_index])
                    chartTopBottomBranchColor.append('#58508D')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Sales Bottom Branch',
                   'data': data,
                   'backgroundColor':'#58508D',
                })

            if topbottom_branch_sort == 'sfl': # Sort From Lowest (Total Sale)
                data = [] 
                for tatb in from_bottom_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_sale_index])
                    chartTopBottomBranchColor.append('#BC5090')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Sales Top Branch',
                   'data': data,
                   'backgroundColor':'#BC5090',
                })

                data = []
                for tatb in from_bottom_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_sale_index])
                    chartTopBottomBranchColor.append('#58508D')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Sales Bottom Branch',
                   'data': data,
                   'backgroundColor':'#58508D',
                })

            
        if topbottom_branch_sort in ['sfht', 'sflt']:
            from_top_data = sorted(results, key=lambda x:x[total_transaction_index], reverse=True) # by total transaction
            from_top_data = from_top_data[:5] # limit to 5 result

            from_bottom_data = sorted(results, key=lambda x:x[total_transaction_index])  # by total transaction
            from_bottom_data = from_bottom_data[:5] # limit to 5 result

            if topbottom_branch_sort == 'sfht': # Sort From Highest (Total Transaction)
                data = []
                for tatb in from_top_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_transaction_index])
                    chartTopBottomBranchColor.append('#BC5090')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Transaction Top Branch',
                   'data': data,
                   'backgroundColor':'#BC5090',
                })

                data = []
                for tatb in from_bottom_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_transaction_index])
                    chartTopBottomBranchColor.append('#58508D')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Transaction Bottom Branch',
                   'data': data,
                   'backgroundColor':'#58508D',
                })

            if topbottom_branch_sort == 'sflt': # Sort From Lowest (Total Transaction)
                data = []
                for tatb in from_bottom_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_transaction_index])
                    chartTopBottomBranchColor.append('#BC5090')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Transaction Top Branch',
                   'data': data,
                   'backgroundColor':'#BC5090',
                })

                data = []
                for tatb in from_bottom_data:
                    labels.append(tatb[branch_name_index])
                    data.append(tatb[total_transaction_index])
                    chartTopBottomBranchColor.append('#58508D')

                arr_chart_topbottom_branch.append({
                   'label': 'Total Transaction Bottom Branch',
                   'data': data,
                   'backgroundColor':'#58508D',
                })


        data = []
        for actb in arr_chart_topbottom_branch:
            for dactb in actb['data']:
                data.append(dactb)

        array_data = [{
           'label': 'Total',
           'data': data,
        }]

        chartTopBottomBranch = {
            'labels': labels,
            'array_data': array_data,
        }

        values = {
            'topbottom_branch_sort': topbottom_branch_sort,
            'topbottom_branch_date': topbottom_branch_date or '',
            'chartTopBottomBranch': chartTopBottomBranch,
            'chartTopBottomBranchcolor': chartTopBottomBranchColor,
        }
        return values

    def sales_overview(self, company, sales_date_compare):
        Monetary = request.env['ir.qweb.field.monetary']
        pos_order_obj = request.env['pos.order'].sudo()
        sales_compare = False

        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59')
        request._cr.execute(f'''
            SELECT 
                COUNT(id), -- total transaction
                COALESCE(SUM(amount_total), 0) -- total sales 
            FROM pos_order  
            WHERE state NOT IN ('draft', 'cancel', 'quotation')
                AND (date_order >= '{start_date}' AND date_order <= '{end_date}')
        ''')
        result = request._cr.fetchall()
        total_transaction = result[0][0]
        total_sales = result[0][1]
        avg_transaction = total_sales and total_transaction and (total_sales / total_transaction) or 0

        total_sales_curr = Monetary.value_to_html(total_sales, {'display_currency': company.currency_id})
        total_sales_curr = total_sales_curr.replace("oe_currency_value","")
        total_sales_curr = total_sales_curr.replace('<span class="">',"")
        total_sales_curr = total_sales_curr.replace("</span>","")

        avg_transaction_curr = Monetary.value_to_html(avg_transaction, {'display_currency': company.currency_id})
        avg_transaction_curr = avg_transaction_curr.replace("oe_currency_value","")
        avg_transaction_curr = avg_transaction_curr.replace('<span class="">',"")
        avg_transaction_curr = avg_transaction_curr.replace("</span>","")

        percentage_total_sales = 0
        percentage_total_transaction = 0
        percentage_avg_sales = 0

        if sales_date_compare:
            sales_compare = True

            start_date_compare = datetime.strptime(sales_date_compare + ' 00:00:00','%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            end_date_compare = datetime.strptime(sales_date_compare + ' 23:59:59','%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            request._cr.execute(f'''
                SELECT 
                    COUNT(id), -- total transaction compare
                    COALESCE(SUM(amount_total), 0) -- total sales compare
                FROM pos_order  
                WHERE state NOT IN ('draft', 'cancel', 'quotation')
                    AND (date_order >= '{start_date_compare}' AND date_order <= '{end_date_compare}')
            ''')
            result = request._cr.fetchall()
            total_transaction_compare = result[0][0]
            total_sales_compare = result[0][1]
            avg_transaction_compare = total_sales_compare and total_transaction_compare and (total_sales_compare / total_transaction_compare) or 0

            if (total_sales_compare > total_sales) and total_sales:
                percentage_total_sales = -round(((total_sales_compare-total_sales)/total_sales_compare) * 100,0)

            if (total_sales_compare < total_sales) and total_sales_compare:
                percentage_total_sales = round(((total_sales-total_sales_compare)/total_sales) * 100,0)

            if (total_transaction_compare > total_transaction) and total_transaction:
                percentage_total_transaction = -round(((total_transaction_compare-total_transaction)/total_transaction_compare) * 100,0)

            if (total_transaction_compare < total_transaction) and total_transaction_compare:
                percentage_total_transaction = round(((total_transaction-total_transaction_compare)/total_transaction) * 100,0)

            if (avg_transaction_compare > avg_transaction) and avg_transaction:
                percentage_avg_sales = -round(((avg_transaction_compare-avg_transaction)/avg_transaction_compare) * 100,0)

            if (avg_transaction_compare < avg_transaction) and avg_transaction_compare:
                percentage_avg_sales = round(((avg_transaction-avg_transaction_compare)/avg_transaction) * 100,0)

        percentage_total_sales = int(percentage_total_sales)
        percentage_total_transaction = int(percentage_total_transaction)
        percentage_avg_sales = int(percentage_avg_sales)

        if percentage_total_sales >= 0:
            percentage_total_sales_str = str(percentage_total_sales) +' %'
            percentage_total_sales_positive = True
        else:
            percentage_total_sales_str = str(percentage_total_sales*-1) +' %'
            percentage_total_sales_positive = False

        if percentage_total_transaction >= 0:
            percentage_total_transaction_str = str(percentage_total_transaction) +' %'
            percentage_total_transaction_positive=True

        else:
            percentage_total_transaction_str = str(percentage_total_transaction*-1) +' %'
            percentage_total_transaction_positive = False

        if percentage_avg_sales >= 0:
            percentage_avg_sales_str = str(percentage_avg_sales) +' %'
            percentage_avg_sales_positive = True
        else:
            percentage_avg_sales_str = str(percentage_avg_sales*-1) +' %'
            percentage_avg_sales_positive = False

        values = {
            'total_sales_curr': total_sales_curr,
            'total_transaction':total_transaction,
            'avg_transaction_curr':avg_transaction_curr,

            'sales_compare': sales_compare,
            'sales_date_compare':sales_date_compare or '',

            'percentage_total_sales_positive':percentage_total_sales_positive,
            'percentage_total_transaction_positive':percentage_total_transaction_positive,
            'percentage_avg_sales_positive':percentage_avg_sales_positive,
            'percentage_total_sales_str':percentage_total_sales_str,
            'percentage_total_transaction_str':percentage_total_transaction_str,
            'percentage_avg_sales_str':percentage_avg_sales_str,
        }
        return values


    def get_actions(self):
        IrUiMenu = request.env['ir.ui.menu'].sudo()
        KsDashboardNinja = request.env['ks_dashboard_ninja.board'].sudo()
        values = {
            'action_sale_dashboard': [],
            'action_promotion_dashboard': [],
            'action_loyalties_dashboard': [],
        }

        check_menu = IrUiMenu.search([('name','=','Sales Dashboard')], limit=1)
        if check_menu and check_menu.action:
            check_board = KsDashboardNinja.search([('ks_dashboard_client_action_id','=',check_menu.action.id)])
            if check_board:
                values['action_sale_dashboard'] = {
                    'name':'Sales Dashboard',
                    'type': 'ir.actions.client',
                    'tag': check_menu.action.tag,
                    'res_model': check_menu.action.res_model,
                    "ks_dashboard_id":check_board.id,
                    'params': {'ks_dashboard_id': check_board.id},
                }

        check_menu = IrUiMenu.search([('name','=','Promotion Dashboard')], limit=1)
        if check_menu and check_menu.action:
            check_board = KsDashboardNinja.search([('ks_dashboard_client_action_id','=',check_menu.action.id)])
            if check_board:
                values['action_promotion_dashboard'] = {
                    'name':'Sales Dashboard',
                    'type': 'ir.actions.client',
                    'tag': check_menu.action.tag,
                    'res_model': check_menu.action.res_model,
                    "ks_dashboard_id":check_board.id,
                    'params': {'ks_dashboard_id': check_board.id},
                }


        check_menu = IrUiMenu.search([('name','=','Loyalties Dashboard')], limit=1)
        if check_menu and check_menu.action:
            check_board = KsDashboardNinja.search([('ks_dashboard_client_action_id','=',check_menu.action.id)])
            if check_board:
                values['action_loyalties_dashboard'] = {
                    'name':'Sales Dashboard',
                    'type': 'ir.actions.client',
                    'tag': check_menu.action.tag,
                    'res_model': check_menu.action.res_model,
                    "ks_dashboard_id":check_board.id,
                    'params': {'ks_dashboard_id': check_board.id},
                }

        return values

    
    def get_sales_performance(self, sales_performance=False):
        hourList = ['07','08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23']

        chart_today_so = []
        chart_today_dict = {}
        chart_1d_so = []
        chart_1d_dict = {}
        chart_2d_so = []
        chart_2d_dict = {}
        chart_3d_so = []
        chart_3d_dict = {}
        chart_4d_so = []
        chart_4d_dict = {}
        chart_5d_so = []
        chart_5d_dict = {}
        chart_6d_so = []
        chart_6d_dict = {}
        chart_7d_so = []
        chart_7d_dict = {}


        start_date = datetime.now().strftime('%Y-%m-%d 00:00:00') 
        end_date = datetime.now().strftime('%Y-%m-%d 23:59:59') 
        query = '''
            SELECT id, date_order, amount_total 
            FROM pos_order  
            WHERE state NOT IN ('draft', 'cancel', 'quotation')
                AND (date_order >= '{start_date}' AND date_order <= '{end_date}')
        '''.format(start_date=start_date, end_date=end_date)
        request._cr.execute(query)
        current_pos_orders = request._cr.fetchall()
        
        for pos_order in current_pos_orders:
            amount_total = pos_order[2]
            date_order = datetime.strptime(str(pos_order[1]),'%Y-%m-%d %H:%M:%S')
            hourTime = date_order.strftime('%H')
            for index_hour in range(0, len(hourList)):
                if hourTime == hourList[index_hour]:
                    if chart_today_dict.get(index_hour):
                        chart_today_dict[index_hour] += amount_total
                    else:
                        chart_today_dict[index_hour] = amount_total
                else:
                    if chart_today_dict.get(index_hour):
                        chart_today_dict[index_hour] += 0
                    else:
                        chart_today_dict[index_hour] = 0

        if sales_performance:
            end_date = datetime.strptime((Datetime.date.today() - Datetime.timedelta(days=1)).strftime('%Y-%m-%d')+' 23:59:59', '%Y-%m-%d %H:%M:%S')
            start_date = datetime.strptime((Datetime.date.today() - Datetime.timedelta(days=7)).strftime('%Y-%m-%d')+' 00:00:00', '%Y-%m-%d %H:%M:%S')
            day_today = Datetime.date.today().strftime("%d")
            query = f'''
                SELECT id, date_order, amount_total 
                FROM pos_order  
                WHERE state NOT IN ('draft', 'cancel', 'quotation')
                    AND (date_order >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND date_order <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}')
            '''
            request._cr.execute(query)
            pos_orders = request._cr.fetchall()

            for pos_order in pos_orders:
                amount_total = pos_order[2] # pos.order -> amount_total
                date_order = pos_order[1] # pos.order -> date_order
                hour = date_order + relativedelta(hours=7)
                hourTime = hour.strftime("%H")

                for index_hour in range(0, len(hourList)):
                    if int(day_today) - int(hour.strftime("%d")) == 1:
                        if hourTime == hourList[index_hour]:
                            if chart_1d_dict.get(index_hour):
                                chart_1d_dict[index_hour] += amount_total
                            else:
                                chart_1d_dict[index_hour] = amount_total
                        else:
                            if chart_1d_dict.get(index_hour):
                                chart_1d_dict[index_hour] += 0
                            else:
                                chart_1d_dict[index_hour] = 0

                    if int(day_today) - int(hour.strftime("%d")) == 2:
                        if hourTime == hourList[index_hour]:
                            if chart_2d_dict.get(index_hour):
                                chart_2d_dict[index_hour] += amount_total
                            else:
                                chart_2d_dict[index_hour] = amount_total
                        else:
                            if chart_2d_dict.get(index_hour):
                                chart_2d_dict[index_hour] += 0
                            else:
                                chart_2d_dict[index_hour] = 0
                    
                    if int(day_today) - int(hour.strftime("%d")) == 3:
                        if hourTime == hourList[index_hour]:
                            if chart_3d_dict.get(index_hour):
                                chart_3d_dict[index_hour] += amount_total
                            else:
                                chart_3d_dict[index_hour] = amount_total
                        else:
                            if chart_3d_dict.get(index_hour):
                                chart_3d_dict[index_hour] += 0
                            else:
                                chart_3d_dict[index_hour] = 0

                    if int(day_today) - int(hour.strftime("%d")) == 4:
                        if hourTime == hourList[index_hour]:
                            if chart_4d_dict.get(index_hour):
                                chart_4d_dict[index_hour] += amount_total
                            else:
                                chart_4d_dict[index_hour] = amount_total
                        else:
                            if chart_4d_dict.get(index_hour):
                                chart_4d_dict[index_hour] += 0
                            else:
                                chart_4d_dict[index_hour] = 0

                    if int(day_today) - int(hour.strftime("%d")) == 5:
                        if hourTime == hourList[index_hour]:
                            if chart_5d_dict.get(index_hour):
                                chart_5d_dict[index_hour] += amount_total
                            else:
                                chart_5d_dict[index_hour] = amount_total
                        else:
                            if chart_5d_dict.get(index_hour):
                                chart_5d_dict[index_hour] += 0
                            else:
                                chart_5d_dict[index_hour] = 0

                    if int(day_today) - int(hour.strftime("%d")) == 6:
                        if hourTime == hourList[index_hour]:
                            if chart_6d_dict.get(index_hour):
                                chart_6d_dict[index_hour] += amount_total
                            else:
                                chart_6d_dict[index_hour] = amount_total
                        else:
                            if chart_6d_dict.get(index_hour):
                                chart_6d_dict[index_hour] += 0
                            else:
                                chart_6d_dict[index_hour] = 0

                    if int(day_today) - int(hour.strftime("%d")) == 7:
                        if hourTime == hourList[index_hour]:
                            if chart_7d_dict.get(index_hour):
                                chart_7d_dict[index_hour] += amount_total
                            else:
                                chart_7d_dict[index_hour] = amount_total
                        else:
                            if chart_7d_dict.get(index_hour):
                                chart_7d_dict[index_hour] += 0
                            else:
                                chart_7d_dict[index_hour] = 0


        for cstd in chart_today_dict:
            chart_today_so.append(chart_today_dict[cstd])
        for cstd in chart_1d_dict:
            chart_1d_so.append(chart_1d_dict[cstd])
        for cstd in chart_2d_dict:
            chart_2d_so.append(chart_2d_dict[cstd])
        for cstd in chart_3d_dict:
            chart_3d_so.append(chart_3d_dict[cstd])
        for cstd in chart_4d_dict:
            chart_4d_so.append(chart_4d_dict[cstd])
        for cstd in chart_5d_dict:
            chart_5d_so.append(chart_5d_dict[cstd])
        for cstd in chart_6d_dict:
            chart_6d_so.append(chart_6d_dict[cstd])
        for cstd in chart_7d_dict:
            chart_7d_so.append(chart_7d_dict[cstd])

        chart_arr_data = [{
            'label': 'Today',
            'data': chart_today_so,
            'borderColor': '#BC5090',
            'backgroundColor':'rgba(255, 255, 255, 0.0)',
            'order': 1
        }]

        if sales_performance:
            order_count = 1
            if '1d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '1D',
                    'data': chart_1d_so,
                    'borderColor': '#C33727',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })
            if '2d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '2D',
                    'data': chart_2d_so,
                    'borderColor': '#58508D',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })

            if '3d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '3D',
                    'data': chart_3d_so,
                    'borderColor': '#66a8e1',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })

            if '4d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '4D',
                    'data': chart_4d_so,
                    'borderColor': '#8deba5',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })

            if '5d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '5D',
                    'data': chart_5d_so,
                    'borderColor': '#2894B4',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })

            if '6d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '6D',
                    'data': chart_6d_so,
                    'borderColor': 'red',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })

            if '7d' in sales_performance:
                order_count+=1
                chart_arr_data.append({
                    'label': '7D',
                    'data': chart_7d_so,
                    'borderColor': 'black',
                    'backgroundColor':'rgba(255, 255, 255, 0.0)',
                    'order': order_count
                })
                
        chart_SP = {
            'label_time': hourList,
            'array_data': chart_arr_data,
        }

        values = {
            'chart_SP': chart_SP,
            'sales_performance': sales_performance,
        }
        return values

    def get_top10_promotion(self, promotion_filter):
        PosPromotion = request.env['pos.promotion'].sudo()
        request._cr.execute( '''
            SELECT pol.promotion_id, count(*)
            FROM pos_order_line as pol 
            INNER JOIN pos_order po ON (pol.order_id = po.id)
            where po.state in %s and pol.promotion_id is not null
            GROUP BY pol.promotion_id 
            ORDER BY count(*) 
            DESC LIMIT 10 ;
        ''' % (tuple(['paid','done']),))

        results = request._cr.fetchall()
        promotion_by_id = {}
        if results:
            promotions = PosPromotion.with_context(active_test=False).search_read([('id','in',[x[0] for x in results])], ['name','no_of_usage'])
            for promotion in promotions:
                promotion_by_id[promotion['id']] = promotion

        chart_data1 = {}
        chart_data2 = {}
        for result in results:
            promotion_id = result[0]
            chart_data1[promotion_id] = result[1]
            chart_data2[promotion_id] = promotion_by_id[promotion_id]['no_of_usage']

        chart_labels = []
        chart_data = []

        chart_promo_used = []
        chart_t_promo_used = []
        if promotion_filter == 's_hpu':
            chart_data2 = sorted(chart_data2.items(), key=lambda x:x[1],reverse=True)
            for data in chart_data2:
                promotion = promotion_by_id[data[0]]
                promo_used_qty = chart_data1[data[0]]
                chart_labels.append(promotion['name'])
                chart_promo_used.append(promo_used_qty)
                chart_t_promo_used.append(data[1])
        else:
            chart_data1 = sorted(chart_data1.items(), key=lambda x:x[1],reverse=True)
            for data in chart_data1:
                promotion = promotion_by_id[data[0]]
                t_promo_used_qty = chart_data2[data[0]]
                chart_labels.append(promotion['name'])
                chart_promo_used.append(data[1])
                chart_t_promo_used.append(t_promo_used_qty)

        if promotion_filter == 's_hpu':
            chart_data.append({
               'label': 'Target Promo Used',
               'data': chart_t_promo_used,
               'backgroundColor':'#61BEEF',
            })
            chart_data.append({
               'label': 'Promo Used',
               'data': chart_promo_used,
               'backgroundColor':'#2C84C7',
            })
        else:
            chart_data.append({
               'label': 'Promo Used',
               'data': chart_promo_used,
               'backgroundColor':'#2C84C7',
            })
            chart_data.append({
               'label': 'Target Promo Used',
               'data': chart_t_promo_used,
               'backgroundColor':'#61BEEF',
            })

        values = {
            'promotion_filter': promotion_filter,
            'chart_labels': chart_labels,
            'chart_data': chart_data,
        }
        return values


    # TODO: Get Total Amount, COGS, Revenue
    def get_chart_TaCR_vals(self):
        days = 7 # Check data start from 7 days ago

        start_date = datetime.strptime((datetime.now()-Datetime.timedelta(days=(days-1))).strftime('%Y-%m-%d 00:00:00'),'%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d 23:59:59'),'%Y-%m-%d %H:%M:%S')

        request._cr.execute(f'''
            SELECT id, date_order, amount_total 
            FROM pos_order  
            WHERE state NOT IN ('draft', 'cancel', 'quotation')
                AND (date_order >= '{start_date}' AND date_order <= '{end_date}')
        ''')
        pos_orders = request._cr.fetchall()

        request._cr.execute(f'''
            SELECT pol.order_id,
                (   
                    COALESCE((
                        SELECT ip.value_float
                        FROM ir_property AS ip
                        WHERE ip.name = 'standard_price' AND ip.res_id = CONCAT('product.product,',  pol.product_id)
                        LIMIT 1
                    ), 0)
                    *
                    pol.qty
                ) AS standard_price_x_qty -- COGS
            FROM pos_order_line AS pol
            INNER JOIN pos_order AS po ON po.id = pol.order_id
            WHERE po.state NOT IN ('draft', 'cancel', 'quotation')
                AND (po.date_order >= '{start_date}' AND po.date_order <= '{end_date}')
        ''')
        pos_order_lines = request._cr.fetchall()

        cogs = []
        revenues = []
        label_date = []
        total_amounts = []
        for i in range(days):
            last_date = datetime.now() - Datetime.timedelta(days=(days-1)-i)
            label_date.append(last_date.strftime("%d - %b"))
            i_cogs = 0
            i_revenue = 0
            i_total_amount = 0

            i_start_date = datetime.strptime(last_date.strftime('%Y-%m-%d 00:00:00'),'%Y-%m-%d %H:%M:%S')
            i_end_date = datetime.strptime(last_date.strftime('%Y-%m-%d 23:59:59'),'%Y-%m-%d %H:%M:%S')
            orders = filter(lambda o: o[1] >= i_start_date and o[1] <= i_end_date, pos_orders)
            if orders:
                order_ids = []
                order_total_amounts = []
                for o in orders:
                    order_ids += [o[0]]
                    order_total_amounts += [o[2]]
                order_lines = filter(lambda o: o[0] in order_ids, pos_order_lines)

                i_cogs = sum([o[1] for o in order_lines])
                i_revenue = i_total_amount - i_cogs
                i_total_amount = sum(order_total_amounts)

            cogs.append(i_cogs)
            revenues.append(i_revenue)
            total_amounts.append(i_total_amount)

        chart_TaCR = {
            'cogs': cogs,
            'revenue': revenues,
            'label_date': label_date,
            'total_amount': total_amounts,
        }
        return { 'chart_TaCR': chart_TaCR }

    @http.route('/get-CashierChangeReport-today', type='http', auth="user")
    def CashierChangeReport(self, **kwargs):
        date_today = datetime.now()
        la_date = calendar.monthrange(int(datetime.strftime(date_today, "%Y")), int(datetime.strftime(date_today, "%m")))[1]
        year_month = datetime.strftime(date_today, "%Y-%m")
        datestart = year_month+'-01 05:00:00'
        datestart = datetime.strptime(datestart, "%Y-%m-%d %H:%M:%S")

        datestart = datestart+ relativedelta(days=-1)
        


        dateend = year_month+'-'+str(la_date)+' 17:59:59'
        dateend = datetime.strptime(dateend, "%Y-%m-%d %H:%M:%S")
        data = request.env['pos.login.history'].sudo().search([('checkin_datetime','>=',datestart),('checkout_datetime','<=',dateend)])
        pdf, _ = request.env.ref('equip3_pos_report.act_report_pos_login_history_report').sudo()._render_qweb_pdf(data.ids)
        return request.make_response(pdf,
            headers=[('Content-Type', 'application/pdf'),
                    ('Content-Disposition', 'attachment; filename=Cashier Change Report.pdf')])
