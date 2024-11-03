from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta

class TeamCustomerSegment(models.Model):
    _name = "team.customer.segment"
    _description = "Sales team wise customer segmentation"

    team_id = fields.Many2one("crm.team", string="Sales team")
    rfm_segment_id = fields.Many2one('setu.rfm.segment', string="RFM Segment")
    total_orders = fields.Integer("Total Orders",compute='_compute_customers', store=True)
    total_revenue = fields.Float("Total Revenue", compute='_compute_customers', store=True)

    @api.depends('rfm_segment_id')
    def _compute_customers(self):
        for team_segment in self:
            past_x_days_sales = self.env['ir.config_parameter'].search([('key','=','past_x_days_sales')])
            if past_x_days_sales:
                from_date = datetime.today() - relativedelta.relativedelta(days=int(past_x_days_sales))
                to_date = datetime.today()
                orders = team_segment.rfm_segment_id.partner_ids.mapped('sale_order_ids').filtered(lambda order: order.date_order > from_date and order.date_order <= to_date and order.state not in ('draft', 'sent', 'cancel') and order.team_id == team_segment.team_id.id)
                team_segment.total_orders = len(orders.ids)
                team_segment.total_revenue = sum(orders.mapped('amount_total'))
