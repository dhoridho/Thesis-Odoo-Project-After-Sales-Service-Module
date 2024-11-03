from odoo import fields, models, api, _
from datetime import date

class ResPartnerRFMSegmentHistory(models.Model):
    _name = 'res.partner.rfm.segment.history'
    _description = """
    Customer RFM segment history table will automatically add records in the table when the customer RFM score will be changed to another one and if the segment value has been changed
    """
    partner_id = fields.Many2one('res.partner', "Customer")
    history_date = fields.Date("History Date")
    old_rfm_segment_id = fields.Many2one("setu.rfm.segment", "Old RFM Segment", help="Customer's Old RFM segment")
    new_rfm_segment_id = fields.Many2one("setu.rfm.segment", "New RFM Segment", help="Customer's New RFM segment")
    old_rfm_score_id = fields.Many2one("setu.rfm.score", "Old RFM Score", help="Customer's Old RFM score")
    new_rfm_score_id = fields.Many2one("setu.rfm.score", "New RFM Score", help="Customer's New RFM score")
    old_segment_rank = fields.Integer("Old Segment Rank")
    new_segment_rank = fields.Integer("New Segment Rank")
    engagement_direction = fields.Integer("Engagement Direction (Up / Down / Consistant)", help="""
        It shows the customer's engagement activities with the business, whether it's increased, decreased or consistant
    """)

class ResPartner(models.Model):
    _inherit='res.partner'

    rfm_segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment", help="""
        Connect RFM score with RFM segment""")
    rfm_score_id = fields.Many2one("setu.rfm.score", "RFM Score", help="RFM score")
    partner_segment_history_ids = fields.One2many("res.partner.rfm.segment.history","partner_id", "Customer Segment History")

    # def write(self, vals):
    #     for partner in self:
    #         current_rfm_segment_id = partner.rfm_segment_id.id
    #         new_rfm_segment_id = vals.get('rfm_segment_id', 0)
    #         if current_rfm_segment_id != new_rfm_segment_id:
    #             self.create_rfm_segment_history()
    #     return super(ResPartner, self).write(vals)

    def create_rfm_segment_history(self, vals):
        rfm_segment_id = self.env['setu.rfm.segment'].search([('id','=',vals.get('rfm_segment_id', False))])
        new_rank = rfm_segment_id and rfm_segment_id.segment_rank or -1
        old_rank = self.rfm_segment_id.segment_rank
        direction = 0
        if old_rank > new_rank:
            direction = -1
        elif old_rank < new_rank:
            direction = 1
        history_vals = {
            'partner_id' : self.id,
            'history_date' : date.now(),
            'old_rfm_segment_id' : self.rfm_segment_id.id,
            'new_rfm_segment_id' : rfm_segment_id or rfm_segment_id.id or False,
            'old_rfm_score_id' : self.rfm_score_id.id,
            'new_rfm_score_id' : vals.get('rfm_score_id', False),
            'old_segment_rank' : old_rank,
            'new_segment_rank' : rfm_segment_id and rfm_segment_id.segment_rank or -1,
            'engagement_direction' : direction,
        }
        self.env['res.partner.rfm.segment.history'].create(history_vals)