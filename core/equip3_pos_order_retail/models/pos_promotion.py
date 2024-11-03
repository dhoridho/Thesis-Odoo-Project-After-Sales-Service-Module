from odoo import api, fields, models, _


class PosPromotion(models.Model):
    _inherit = "pos.promotion"

    pos_apply = fields.Many2many(comodel_name='pos.config', string="Apply in POS")
    card_payment_id = fields.Many2one('card.payment', string="Card Payment")
    def apply_to_selected_pos(self):
        if self.pos_apply:
            for pos_config_obj in self.pos_apply:
                pos_config_obj.promotion_ids = [(4, self.id)]
