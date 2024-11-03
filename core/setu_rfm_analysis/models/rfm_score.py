from odoo import fields, models, api, _

class SetuRFMScore(models.Model):
    _name = 'setu.rfm.score'
    _description="RFM score helps to define RFM segment criteria."

    name = fields.Char("RFM Score")
    rfm_segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment", help="""
    Connect RFM score with RFM segment""")
    recency = fields.Selection([('1','1'),
                                ('2','2'),
                                ('3','3'),
                                ('4','4')], "Recency", help=""""
        Recency, Rank your customers according to the number of days since customer's last purchase """)
    frequency = fields.Selection([('1', '1'),
                                ('2', '2'),
                                ('3', '3'),
                                ('4', '4')], "Frequency", help=""""
            Frequency, Rank your customers according to the number of times customer place an order (ordering frequency) """)
    monetization = fields.Selection([('1', '1'),
                                ('2', '2'),
                                ('3', '3'),
                                ('4', '4')], "Monetization", help=""""
            Monetization, Rank your customers according to Customer's total orders value """)

    description = fields.Text("Description", help="Customer activity")
    partner_ids = fields.One2many("res.partner", "rfm_score_id", "Customers")
    total_customers = fields.Integer("Total Customers", compute='_compute_customers')

    @api.depends('partner_ids')
    def _compute_customers(self):
        for score in self:
            score.total_customers = len(score.partner_ids)

    @api.onchange('recency', 'frequency', 'monetization')
    def onchange_rfm_score(self):
        score = self.recency + self.frequency + self.monetization
        self.name = score