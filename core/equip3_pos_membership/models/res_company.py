# -*- coding: utf-8 -*-

from odoo import api, models, fields, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    is_pos_use_deposit = fields.Boolean('Deposit')
    membership_pluspoint_rounding = fields.Boolean(string="Membership PlusPoint Rounding")
    membership_pluspoint_rounding_type = fields.Selection(
        [('Up','Up'), ('Down','Down'), ('Half Up','Half Up')], 
        string="Membership PlusPoint Rounding Type", default='Down')
    membership_pluspoint_rounding_multiplier = fields.Selection(
        [('0.05','0.05'), ('0.1','0.1'), ('0.5','0.5'), ('1','1'), ('10','10'), ('100','100'), ('500','500'), ('1000','1000')], 
        string="Membership PlusPoint Rounding Multiplier", default='1')
