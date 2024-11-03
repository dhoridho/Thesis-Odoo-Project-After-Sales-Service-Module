# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request
import datetime

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_count_listl(self):
        uid = request.session.uid 
        user_id=self.env['res.users'].browse(uid)
        total_ser = self.sudo().search_count([('user_id', '=', uid)])
        search_quotation = self.search([('state', 'in', ['draft'])])
        calulate_quotation = len(search_quotation)
        search_sale = self.search([('state', 'in', ['sale'])])
        calculate_sale = len(search_sale)
        search_quotation_sent = self.search([('state', 'in', ['sent'])])
        calculate_quotation_sent = len(search_quotation_sent)
        search_cancel = self.search([('state', 'in', ['cancel'])])
        calculate_cancel = len(search_cancel)
        account_move_search = self.env['account.move']
        search_fully_invoiced = self.search([('invoice_status', 'in', ['no'])])
        calculate_fully_invoice = len(search_fully_invoiced)
        data_obj = self.env['res.partner']      
        list_data = data_obj.search([])
        calculate_partner = len(list_data)
        sale_search_view_id = self.env.ref('sale.view_sales_order_filter')
        record = self.env['res.partner'].search([('id','=',10)])
        customer_list = len(record)


        return {
            'quotation_count' : calulate_quotation,
            'sale_count' : calculate_sale,
            'partner_count' : calculate_partner,
            'quotation_sent_count':calculate_quotation_sent,
            'cancel_count':calculate_cancel,
            'fully_invoice' : calculate_fully_invoice,
            'count_c' : customer_list,

           
        
          }

    @api.model
    def get_sale_table(self):
        sql_query = """
            SELECT so.name AS order_reference, rs.name AS partner_name,so.date_order AS date_order,
            so.amount_total AS amount
            FROM sale_order so INNER JOIN res_partner rs ON (so.partner_id = rs.id)
            WHERE so.state = 'sale'  
            ORDER BY order_reference ASC LIMIT 10
            

        """
        self._cr.execute(sql_query)
        sale_table = self._cr.dictfetchall()

        sql_query = """
           SELECT so.name AS order_reference,rs.name AS partner_name,so.date_order AS date_order
            FROM sale_order so INNER JOIN res_partner rs ON (so.partner_id = rs.id)
            WHERE so.state = 'cancel'  

        """
        self._cr.execute(sql_query)
        sale_cancel_order = self._cr.dictfetchall()


        sql_query = """
           SELECT so.name AS order_reference,rs.name AS partner_name,so.date_order AS date_order,
           so.commitment_date AS delievery_date
            FROM sale_order so INNER JOIN res_partner rs ON (so.partner_id = rs.id)
            WHERE so.state = 'sent'  

        """
        self._cr.execute(sql_query)
        quotation_sent = self._cr.dictfetchall()


        sql_query = """
        SELECT distinct rs.name AS customer_name
        FROM sale_order so INNER JOIN res_partner rs ON (so.partner_id = rs.id)
            WHERE rs.id IN (14,10,26,11);


        """
        self._cr.execute(sql_query)
        customers = self._cr.dictfetchall()

        return {
            
            'sale_tables': sale_table,
            'sale_cancel': sale_cancel_order,
            'order': quotation_sent,
            'count_customer': customers
          }


    @api.model
    def get_sale_order_value(self):
        sale_order = self.env['sale.order']


    @api.model
    def get_value(self):
        cr = self._cr

        query = """
          SELECT cl.partner_id AS partner_name,count(*),rs.name AS partner_name
            FROM sale_order cl INNER JOIN res_partner rs ON (cl.partner_id = rs.id)
            group by cl.partner_id,rs.name
            order by cl.partner_id

        """
                
    
        cr.execute(query)
        payroll_data = cr.dictfetchall()
        payroll_label = []
        payroll_dataset = []
        data_set = {}
        for data in payroll_data:
            payroll_label.append(data['partner_name'])
            payroll_dataset.append(data['count'])
           
        data_set.update({"payroll_dataset":payroll_dataset})
        data_set.update({"payroll_label":payroll_label})
        return data_set



    @api.model
    def get_value_price(self):
        cr = self._cr

        query = """
          SELECT cl.partner_id AS partner_name,max(amount_total) as price,rs.name AS partner_name
            FROM sale_order cl INNER JOIN res_partner rs ON (cl.partner_id = rs.id)
            group by cl.partner_id,rs.name
            order by cl.partner_id

        """
                
    
        cr.execute(query)
        payroll_data = cr.dictfetchall()
        payroll_label = []
        payroll_dataset = []
        data_set = {}
        for data in payroll_data:
            payroll_label.append(data['partner_name'])
            payroll_dataset.append(data['price'])
        data_set.update({"payroll_dataset":payroll_dataset})
        data_set.update({"payroll_label":payroll_label})
        return data_set






    @api.model
    def get_recent_sale_order(self):
        cr = self._cr

        query = """
          SELECT pt.name AS product_name,pt.list_price  as product_price
            FROM product_template pt 
            order by pt.name desc limit 4

        """
                
        cr.execute(query)
        payroll_data = cr.dictfetchall()
        payroll_label = []
        payroll_dataset = []
        data_set = {}
        for data in payroll_data:
            payroll_label.append(data['product_name'])
            payroll_dataset.append(data['product_price'])
        data_set.update({"payroll_dataset":payroll_dataset})
        data_set.update({"payroll_label":payroll_label})
        return data_set



    @api.model
    def get_customer_detail(self):
        cr = self._cr

        query = """
        SELECT distinct so.name as name, rs.name,count(*)  as  count
        from sale_order so join res_partner rs on so.partner_id =rs.id   
        group by rs.name,so.name
        order by  so.name desc limit 8

        """
                
        cr.execute(query)
        payroll_data = cr.dictfetchall()
        payroll_label = []
        payroll_dataset = []
        data_set = {}
        for data in payroll_data:
            payroll_label.append(data['name'])
            payroll_dataset.append(data['count'])
        data_set.update({"payroll_dataset":payroll_dataset})
        data_set.update({"payroll_label":payroll_label})
        return data_set




    @api.model
    def get_salesperson(self):
        cr = self._cr

        query = """
            
        SELECT so.name as name, rs.name,count(*) 
        from sale_order so join res_partner rs on so.partner_id =rs.id   
        group by rs.name,so.name
        order by  so.name desc limit 2
        
        """
                
        cr.execute(query)
        payroll_data = cr.dictfetchall()
        payroll_label = []
        payroll_dataset = []
        data_set = {}
        for data in payroll_data:
            payroll_label.append(data['name'])
            payroll_dataset.append(data['count'])
        data_set.update({"payroll_dataset":payroll_dataset})
        data_set.update({"payroll_label":payroll_label})
        return data_set



    @api.model
    def get_sale_team_info(self):
        cr = self._cr

        query = """
            
       SELECT so.team_id as name, cl.name,count(*) 
        from sale_order so left join crm_team cl on so.team_id = cl.id   
        group by cl.name,so.team_id
        order by  so.team_id 
        
        """
                
        cr.execute(query)
        st_data = cr.dictfetchall()
        st_label = []
        st_dataset = []
        data_set = {}
        for data in st_data:
            st_label.append(data['name'])
            st_dataset.append(data['count'])
        data_set.update({"st_dataset":st_dataset})
        data_set.update({"st_label":st_label})
        return data_set



    @api.model
    def get_r_sale_info(self):
        cr = self._cr

        query = """
            
       SELECT so.name as sale_order_name, ao.invoice_origin,count(*) 
        from sale_order so left join account_move ao on so.id = ao.id   
        group by so.name,ao.invoice_origin
        order by  ao.invoice_origin desc limit 5
        """  
                
        cr.execute(query)
        r_data = cr.dictfetchall()
        r_label = []
        r_dataset = []
        data_set = {}
        for data in r_data:
            r_label.append(data['sale_order_name'])
            r_dataset.append(data['count'])
        data_set.update({"r_dataset":r_dataset})
        data_set.update({"r_label":r_label})
        return data_set

