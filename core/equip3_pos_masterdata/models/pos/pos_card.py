# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class PosGroupCard(models.Model):
    _name = 'group.card'
    _rec_name = 'card_group_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    card_group_img = fields.Binary(tracking=True)
    card_group_name = fields.Char(string="Group Card", tracking=True)
    card_group_active = fields.Boolean(string="Active in Point of Sale", tracking=True)

    company_id = fields.Many2one('res.company',string= "Company",default=lambda self: self.env.company.id ,tracking=True)

class PosCardPayment(models.Model):
    _name = 'card.payment'
    _rec_name = 'card_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    card_img = fields.Binary(tracking=True)
    card_name = fields.Char(string="Card", tracking=True)
    card_active = fields.Boolean(string = "Active in Point of Sale", tracking=True)
    card_group = fields.Many2one('group.card', string = "Group Card", tracking=True)
    BIN = fields.Char(string = "BIN", tracking=True)

    company_id = fields.Many2one('res.company',string= "Company",default=lambda self: self.env.company.id , tracking=True)
    have_char = fields.Boolean('Allow Alpha Numeric')
    card_type = fields.Selection([('Credit','Credit'), ('Debit','Debit')], string="Type")
    card_status = fields.Char('Status',compute='_compute_card_status')


    def _compute_card_status(self):
        for data in self:
            card_status = 'Not Active'
            if data.card_active:
                card_status = 'Active'
            data.card_status = card_status

    @api.constrains('BIN')
    def check_BIN(self):
        if self.BIN:
            if len(self.BIN) != 6 :
                raise UserError('A BIN card should have 6-digit numbers')
    