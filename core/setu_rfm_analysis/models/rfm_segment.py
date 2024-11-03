from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta

class SetuRFMSegment(models.Model):
    _name = 'setu.rfm.segment'
    _description="""
        The  idea is to segment customers based on when their last purchase was, 
        how often they’ve purchased in the past, and how much they’ve spent overall. 
        All three of these measures have proven to be effective predictors of a customer's willingness to engage in marketing messages and offers.
    """
    _order = "segment_rank"

    name = fields.Char("Name")
    segment_description = fields.Text("Activity Descripton", help=""""
    use description to identify who they are.     
    """)
    actionable_tips = fields.Text("Actionable Tips", help="Suggest recommended marketting action for the segment.")
    rfm_score_ids = fields.One2many("setu.rfm.score", "rfm_segment_id", "RFM Scores")
    rfm_score_syntax = fields.Text("RFM Score Syntax")
    rfm_score_condition = fields.Text("RFM Score Condition")
    segment_rank = fields.Integer("Rank")
    partner_ids = fields.One2many("res.partner", "rfm_segment_id", "Customers")
    order_ids = fields.One2many("sale.order", "rfm_segment_id", "Sale orders")
    mailing_ids = fields.One2many("mailing.mailing", "rfm_segment_id", "Mailing")
    total_mailing = fields.Integer("Total Mailing", compute='_compute_mailing')

    total_customers = fields.Integer("Total Customers", compute='_compute_customers', tracking=1)
    total_orders = fields.Integer("Total Orders",compute='_compute_customers', tracking=2)
    total_revenue = fields.Float("Total Revenue",compute='_compute_customers', tracking=3)
    team_customer_segment_ids = fields.One2many("team.customer.segment", "rfm_segment_id", string="Team customer segment")

    open_lead_count = fields.Integer("Open Leads", compute='_calculate_leads')
    open_rfq_count = fields.Integer("Request for Quotation", compute='_calculate_rfq')

    total_customers_ratio = fields.Float("Customers", compute='_calculate_ratio', tracking=4)
    total_orders_ratio = fields.Float("Orders", compute='_calculate_ratio', tracking=5)
    total_revenue_ratio = fields.Float("Revenue", compute='_calculate_ratio', tracking=6)
    from_date = fields.Date("From Date")
    to_date = fields.Date("From Date")
    calculated_on = fields.Date("Calculated On")

    def _compute_mailing(self):
        for segment in self:
            segment.total_mailing = len(segment.mailing_ids.ids)

    def _calculate_leads(self):
        won_stage = self.env['crm.stage'].search([('is_won','=',True)])
        for segment in self:
            leads = self.env['crm.lead'].search([('stage_id','not in',won_stage.ids),('partner_id','in',segment.partner_ids.ids)])
            segment.open_lead_count = leads and len(leads.ids) or 0

    def _calculate_rfq(self):
        for segment in self:
            orders = self.env['sale.order'].search([('state', 'in', ['draft', 'sent']),('partner_id','in',segment.partner_ids.ids)])
            segment.open_rfq_count = orders and len(orders.ids) or 0

    def _compute_customers(self):
        for segment in self:
            segment.update({
            'total_customers' : len(segment.partner_ids),
            'total_orders' : len(segment.order_ids),
            'total_revenue' : sum(segment.mapped('order_ids').mapped('amount_total')),
            })

    def _calculate_ratio(self):
        segments = self.env['setu.rfm.segment'].search([])
        overall_customers = len(segments.mapped('partner_ids').ids)
        overall_orders = len(segments.mapped('order_ids').ids)
        overall_revenue = sum(segments.mapped('order_ids').mapped('amount_total'))

        for segment in self:
            segment.update({
                'total_customers_ratio': overall_customers and round((segment.total_customers / overall_customers) * 100.0, 2) or 0.01,
                'total_orders_ratio': overall_orders and round((segment.total_orders / overall_orders) * 100.0, 2) or 0.01,
                'total_revenue_ratio': overall_revenue and round((segment.total_revenue / overall_revenue) * 100.0, 2) or 0.01,
            })

    def open_mailing(self):
        kanban_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_kanban').id
        form_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_form').id
        tree_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_tree').id
        graph_view_id = self.env.ref('mass_mailing.view_mail_mass_mailing_graph').id
        report_display_views = [(kanban_view_id, 'kanban'), (tree_view_id, 'tree'), (form_view_id, 'form'), (graph_view_id, 'graph')]
        return {
            'name': _('Mailings'),
            'domain': [('id', 'in', self.mailing_ids.ids)],
            'res_model': 'mailing.mailing',
            'view_mode': "kanban,tree,form,graph",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_customer(self):
        kanban_view_id = self.env.ref('base.res_partner_kanban_view').id
        tree_view_id = self.env.ref('base.view_partner_tree').id
        form_view_id = self.env.ref('base.view_partner_form').id
        report_display_views = [(kanban_view_id, 'kanban'), (form_view_id, 'form'), (tree_view_id, 'tree')]
        return {
            'name': _('Customers'),
            'domain': [('id', 'in', self.partner_ids.ids)],
            'res_model': 'res.partner',
            'view_mode': "kanban,form,tree",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_orders(self):
        form_view_id = self.env.ref('sale.view_order_form').id
        tree_view_id = self.env.ref('sale.view_order_tree').id
        report_display_views = [(tree_view_id, 'tree'), (form_view_id, 'form')]
        return {
            'name': _('Sales Order'),
            'domain': [('id', 'in', self.order_ids.ids)],
            'res_model': 'sale.order',
            'view_mode': "tree,form",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_leads(self):
        kanban_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
        form_view_id = self.env.ref('crm.crm_lead_view_form').id
        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        report_display_views = [(kanban_view_id, 'kanban'),(tree_view_id, 'tree'), (form_view_id, 'form')]
        won_stage = self.env['crm.stage'].search([('is_won', '=', True)])

        return {
            'name': _('Leads'),
            'domain': [('stage_id', 'not in', won_stage.ids), ('partner_id', 'in', self.partner_ids.ids)],
            'res_model': 'crm.lead',
            'view_mode': "kanban,tree,form",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def open_rfqs(self):
        form_view_id = self.env.ref('sale.view_order_form').id
        tree_view_id = self.env.ref('sale.view_quotation_tree_with_onboarding').id
        report_display_views = [(tree_view_id, 'tree'), (form_view_id, 'form')]

        return {
            'name': _('Quotation'),
            'domain': [('state', 'in', ['draft', 'sent']), ('partner_id', 'in', self.partner_ids.ids)],
            'res_model': 'sale.order',
            'view_mode': "tree,form",
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_mailing(self):
        mailing_env = self.env['mailing.mailing']
        email = self.env.user.partner_id.email or self.env.user.partner_id.company_id and self.env.user.partner_id.company_id.email
        mailing_vals = {
            'name' : '%s customers' % self.name,
            'mailing_model_id' : self.env.ref('base.model_res_partner').id,
            'subject' : 'Mailing for %s customers' % self.name,
            'mailing_domain' : [("rfm_segment_id","=",self.id)],
            'user_id' : self.env.user.id,
            'email_from' : email,
            'reply_to' : email,
            'mail_server_id' : mailing_env._get_default_mail_server_id(),
            'medium_id' : self.env.ref('utm.utm_medium_email').id,
            'rfm_segment_id' : self.id,
        }
        mailing_env.create(mailing_vals)
        return self.open_mailing()

    @api.model
    def update_customer_segment(self):
        past_x_days_sales = self.env['ir.config_parameter'].sudo().get_param('setu_rfm_analysis.past_x_days_sales')
        if past_x_days_sales:
            date_begin = datetime.today() - relativedelta.relativedelta(days=int(past_x_days_sales))
            date_end = datetime.today()

        query = """
                Select * from update_customer_rfm_segment('{}','%s','%s')
            """%(date_begin, date_end)
        print(query)
        self._cr.execute(query)

    @api.model
    def _create_sp(self):
        self.create_sp_get_rfm_analysis_data()
        self.create_sp_update_customer_rfm_segment()

    @api.model
    def create_sp_get_rfm_analysis_data(self):
        query = """
            -- DROP FUNCTION public.get_rfm_analysis_data(integer[], date, date);

            CREATE OR REPLACE FUNCTION public.get_rfm_analysis_data(
                IN company_ids integer[],
                IN start_date date,
                IN end_date date)
              RETURNS TABLE(company_id integer, customer_id integer, total_orders integer, total_order_value numeric, days_from_last_purchase integer, recency integer, frequency integer, monetization integer, score character varying, score_id integer, segment_id integer) AS
            $BODY$
            BEGIN	
                    Drop Table if exists rfm_transaction_table;
                CREATE TEMPORARY TABLE rfm_transaction_table(
                    company_id integer,  customer_id integer,
                    total_orders integer, total_order_value numeric, days_from_last_purchase integer
                );

                insert into rfm_transaction_table
                Select 
                    so.company_id,
                    so.partner_id, 
                    count(so.id) as total_orders,		
                    sum(Round(so.amount_total / 
                    CASE COALESCE(so.currency_rate, 0::numeric)
                        WHEN 0 THEN 1.0
                        ELSE so.currency_rate
                    END, 2)) as total_order_value,
                    DATE_PART('day', now()::timestamp - max(so.date_order)::timestamp) as days_from_last_purchase
                From
                    Sale_order so 
                Where so.state not in ('draft','cancel','sent')	
                and so.date_order::date >= start_date and so.date_order::date <= end_date
                and 1 = case when array_length(company_ids,1) >= 1 then 
                    case when so.company_id = ANY(company_ids) then 1 else 0 end
                    else 1 end
                group by so.partner_id, so.company_id;

                Return Query
                with all_data as (
                    Select 
                    row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.days_from_last_purchase) as recency_id,
                    row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.total_orders desc) as frequency_id,
                    row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.total_order_value desc) as monetization_id,
                    * 
                    from rfm_transaction_table rtt
                ), 
                customer_count as (
                    Select rtt.company_id, count(rtt.customer_id) as total_customers from rfm_transaction_table rtt
                    group by rtt.company_id
                )
                Select D.*, (D.recency::char || D.frequency::char || D.monetization::char)::character varying as score,
                    rsc.id as score_id,
                    rsc.rfm_segment_id
                from 
                (
                    Select 
                        ad.company_id, ad.customer_id, 
                        ad.total_orders, ad.total_order_value, ad.days_from_last_purchase,
                        case 
                            when ((recency_id * 100.0) / total_customers) < 26 then 1
                            when ((recency_id * 100.0) / total_customers) >= 26 and ((recency_id * 100.0) / total_customers) < 51 then 2
                            when ((recency_id * 100.0) / total_customers) >= 51 and ((recency_id * 100.0) / total_customers) < 76 then 3
                            when ((recency_id * 100.0) / total_customers) >= 76 then 4
                        end as recency, 
                        case 
                            when ((frequency_id * 100.0) / total_customers) < 26 then 1
                            when ((frequency_id * 100.0) / total_customers) >= 26 and ((frequency_id * 100.0) / total_customers) < 51 then 2
                            when ((frequency_id * 100.0) / total_customers) >= 51 and ((frequency_id * 100.0) / total_customers) < 76 then 3
                            when ((frequency_id * 100.0) / total_customers) >= 76 then 4
                        end as frequency, 
                        case 
                            when ((monetization_id * 100.0) / total_customers) < 26 then 1
                            when ((monetization_id * 100.0) / total_customers) >= 26 and ((monetization_id * 100.0) / total_customers) < 51 then 2
                            when ((monetization_id * 100.0) / total_customers) >= 51 and ((monetization_id * 100.0) / total_customers) < 76 then 3
                            when ((monetization_id * 100.0) / total_customers) >= 76 then 4
                        end as monetization		
                    From 
                        all_data ad 
                            Inner Join customer_count cc on cc.company_id = ad.company_id
                )D
                    Inner Join setu_rfm_score rsc on rsc.name = (D.recency::char || D.frequency::char || D.monetization::char)::character varying;


            END; 
            $BODY$
              LANGUAGE plpgsql VOLATILE
              COST 100
              ROWS 1000;
        """
        self.env.cr.execute(query)

    @api.model
    def create_sp_update_customer_rfm_segment(self):
        query = """
            -- DROP FUNCTION public.update_customer_rfm_segment(integer[], date, date);

            CREATE OR REPLACE FUNCTION public.update_customer_rfm_segment(
                company_ids integer[],
                start_date date,
                end_date date)
              RETURNS void AS
            $BODY$
            BEGIN	

                update sale_order set rfm_segment_id = null where rfm_segment_id is not null;
        
            update res_partner cust set rfm_score_id = D.score_id, rfm_segment_id = D.segment_id 
            From (
            Select * from get_rfm_analysis_data(company_ids, start_date, end_date) T ) D	
            Where D.customer_id = cust.id;
        
            update sale_order so set rfm_segment_id = orders.rfm_segment_id from 
            (
                Select 
                    so.partner_id, 
                    so.id as order_id,
                    partner.rfm_segment_id
                From
                    sale_order so 
                        Inner join res_partner partner on partner.id = so.partner_id
                Where so.state not in ('draft','cancel','sent')	
                and so.date_order::date >= start_date and so.date_order::date <= end_date
                and 1 = case when array_length(company_ids,1) >= 1 then 
                    case when so.company_id = ANY(company_ids) then 1 else 0 end
                    else 1 end
            )orders
            where orders.order_id = so.id;

	   update setu_rfm_segment set from_date = start_date, to_date = end_date, calculated_on= (select now()::date);

            END; 
            $BODY$
              LANGUAGE plpgsql VOLATILE
              COST 100;
        """
        self.env.cr.execute(query)


