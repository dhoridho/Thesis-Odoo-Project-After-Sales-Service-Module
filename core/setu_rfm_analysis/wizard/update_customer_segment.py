from odoo import fields, models, api
from datetime import datetime
from dateutil import relativedelta

class UpdateCustomerSegment(models.TransientModel):
    _name = 'update.customer.segment'
    _description = "Update Customer Segment"

    def _default_end_date(self):
        past_x_days_sales = self.env['ir.config_parameter'].sudo().get_param('setu_rfm_analysis.past_x_days_sales')
        if past_x_days_sales:
            return datetime.today() - relativedelta.relativedelta(days=int(past_x_days_sales))

    def _get_default_note(self):
        segment = self.env['setu.rfm.segment'].search([],limit=1)

        if segment and segment.calculated_on and segment.from_date and segment.to_date:
            return """
                Past sales history has been taken from %s to %s to calculate RFM segment.
                RFM segment calculation was made last on %s 
            """%(segment.from_date, segment.to_date, segment.calculated_on)

    date_begin = fields.Date(
            string='Start Date', required=True,
            tracking=True, default=_default_end_date)
    date_end = fields.Date(
            string='End Date', required=True,
            tracking=True, default=datetime.today())
    note = fields.Text("Note", default=_get_default_note)


    def update_customer_segment(self):
        query = """
                Select * from update_customer_rfm_segment('{}','%s','%s')
            """%(self.date_begin, self.date_end)
        print(query)
        self._cr.execute(query)
