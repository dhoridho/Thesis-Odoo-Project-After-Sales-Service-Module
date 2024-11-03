# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api
import random


class ShQualityAlert(models.Model):
    _name = 'sh.quality.alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Quality Alert'
    _rec_name = 'name'

    name = fields.Char("Name", readonly=True)
    title = fields.Char('Title')
    product_id = fields.Many2one(
        'product.product', 'Product', required=True)
    lot_id = fields.Many2one('stock.production.lot',
                             'Lot Number')
    user_id = fields.Many2one('res.users', 'Responsible',
                              required=True, default=lambda self: self.env.user)
    team_id = fields.Many2one('sh.qc.team', 'Team',
                               required=True)
    sh_priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), (
        '2', 'Normal'), ('3', 'High')], string="Priority")
    tag_ids = fields.Many2many('sh.qc.alert.tags', string="Tags")
    color = fields.Integer(string='Color Index')
    sh_description = fields.Html('Description')
    partner_id = fields.Many2one('res.partner', 'Partner')
    stage_id = fields.Many2one('sh.qc.alert.stage', 'Stage')
    piking_id = fields.Many2one('stock.picking', 'Picking Ref.')
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        number = random.randrange(1, 10)
        if 'company_id' in vals:
            vals['color'] = number
            seq = self.env['ir.sequence'].next_by_code('sh.quality.alert')
            vals['name'] = seq
        return super(ShQualityAlert, self).create(vals)
