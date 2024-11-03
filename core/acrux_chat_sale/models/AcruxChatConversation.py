# -*- coding: utf-8 -*-
from odoo import models
from odoo import fields
from odoo import api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.addons.acrux_chat.tools import phone_format


class AcruxChatConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    sale_order_id = fields.Many2one('sale.order', 'Sale Order', ondelete='set null')
    partner_sellman_id = fields.Many2one('res.users', related='res_partner_id.user_id',
                                         store=False)

    @api.model
    def get_to_done(self):
        out = super(AcruxChatConversation, self).get_to_done()
        out['sale_order_id'] = False
        return out

    @api.model
    def get_to_current(self):
        out = super(AcruxChatConversation, self).get_to_current()
        out['sale_order_id'] = False
        return out

    @api.model
    def get_to_new(self):
        out = super(AcruxChatConversation, self).get_to_new()
        out['sale_order_id'] = False
        return out

    def get_fields_to_read(self):
        out = super(AcruxChatConversation, self).get_fields_to_read()
        out.extend(['res_partner_id', 'sale_order_id', 'partner_sellman_id'])
        return out

    def save_res_partner(self, res_partner_id):
        self.ensure_one()
        self.write({'res_partner_id': res_partner_id})
        return {'partner': [self.res_partner_id.id, self.res_partner_id.name],
                'partner_sellman': [self.partner_sellman_id.id, self.partner_sellman_id.name]}

    def save_sale_order(self, sale_order_id):
        self.ensure_one()
        self.write({'sale_order_id': sale_order_id})
        sale_id = self.env['sale.order'].browse(sale_order_id)
        sale_id.conversation_id = self.id
        return [self.sale_order_id.id, self.sale_order_id.name]

    @api.model
    def conversation_create(self, partner_id, id_connector=False, number=False):
        ''' Set 'number' if not take from partner. '''
        def validate_number(partner_id, number):
            number = number or partner_id.mobile or partner_id.phone
            if not number:
                raise ValidationError(_('Partner does not have mobile number'))
            return phone_format(number.lstrip('+'), partner_id.country_id)

        if not id_connector:
            id_connector = self.env['acrux.chat.connector'].search([], limit=1).id
        number = validate_number(partner_id, number)
        conv_id = self.create({'name': partner_id.name,
                               'number': number,
                               'connector_id': id_connector,
                               'res_partner_id': partner_id.id,
                               'status': 'current',
                               'sellman_id': self.env.user.id})
        return conv_id
