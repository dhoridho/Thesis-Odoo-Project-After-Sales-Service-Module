from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta

class CustomerSegmentAnalysis(models.TransientModel):
    _name = 'customer.segment.analysis'
    description = "Customer Segment Analysis"

    partner_id = fields.Many2one("res.partner", "Customers")
    rfm_score_id = fields.Many2one("setu.rfm.score", "RFM Scores")
    rfm_segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment")

    days_from_last_purchase = fields.Integer("Days from last purchase")
    total_orders = fields.Integer("Total Orders")
    total_revenue = fields.Float("Total Revenaue")
    total_order_percentage = fields.Float("Total Orders (%)")
    total_revenue_percentage = fields.Float("Total Revenue (%)")

    def get_customer_segment_analysis(self):
        """
        :return:
        """
        query = "Select * from get_customer_segment_analysis_data()"
        print(query)
        self._cr.execute(query)
        customer_segment_data = self._cr.dictfetchall()
        return  customer_segment_data

    def download_report_in_listview(self):
        stock_data = self.get_inventory_fsn_analysis_report_data()
        print (stock_data)
        for fsn_data_value in stock_data:
            fsn_data_value['wizard_id'] = self.id
            self.create_data(fsn_data_value)

        graph_view_id = self.env.ref('setu_advance_inventory_reports.setu_inventory_fsn_analysis_bi_report_graph').id
        tree_view_id = self.env.ref('setu_advance_inventory_reports.setu_inventory_fsn_analysis_bi_report_tree').id
        is_graph_first = self.env.context.get('graph_report',False)
        report_display_views = []
        viewmode = ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((tree_view_id, 'tree'))
            viewmode="graph,tree"
        else:
            report_display_views.append((tree_view_id, 'tree'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode="tree,graph"
        return {
            'name': _('Inventory FSN Analysis'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.inventory.fsn.analysis.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }
