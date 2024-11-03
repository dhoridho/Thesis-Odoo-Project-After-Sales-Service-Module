# -*- coding: utf-8 -*-

import uuid
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class AcruxChatConnector(models.Model):
    _name = 'acrux.chat.connector'
    _description = 'Connector Definition'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Priority', required=True, default=1)
    message = fields.Text('Message')
    connector_type = fields.Selection([('generic', 'Generic')], string='Connect to',
                                      default='generic', required=True,
                                      help='Type for connector, every new connector has to add its own type')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    team_id = fields.Many2one('crm.team', string='Team',
                              default=lambda self: self.env.ref('acrux_chat.chatroom_team'),
                              ondelete='set null')
    verify = fields.Boolean('Verify SSL', default=True, help='Set False if SSLError: bad handshake - ' +
                                                             'certificate verify failed.')
    # App connection
    source = fields.Char('Phone (or Source)', help='If required. Phone or identifier.\n' +
                                                   'For WhatsApp is the phone number.')
    channel = fields.Char('Channel', default='whatsapp', help='If required')
    endpoint = fields.Char('API Endpoint', required=True, default='https://', help='API Url to connect')
    apikey = fields.Char('API key', required=True, default='key', help='API key or token')
    sandbox = fields.Boolean('Test Mode', default=True)
    uuid = fields.Char('Unique identifier', required=True, default=lambda _x: uuid.uuid4().hex[:10],
                       copy=False, help='To set unique WebHook or resource')
    time_to_respond = fields.Integer('Time to Respond (Hours)', default=23,
                                     help='Expiry time in hours to respond message without additional fee.\n' +
                                     'Null or 0 indicate no limit.')
    time_to_reasign = fields.Integer('Time to reasign (Minutes)', default=2,
                                     help='Time in which the conversation is released to be taken by another user.')
    border_color = fields.Char(string="Border Color", size=7, default="#FFFFFF", required=True,
                               help="Border color to differentiate conversation connector")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', _('Name must be unique.')),
        ('uuid_uniq', 'unique (uuid)', _('Identifier must be unique.')),
    ]

    @api.onchange('company_id')
    def _onchange_company_id(self):
        return {
            'domain': {'team_id': [('company_id', '=', self.company_id.id)]},
        }

    @api.constrains('border_color')
    def constrains_border_color(self):
        for r in self:
            if r.border_color != '#FFFFFF':
                if self.search_count([('border_color', '=', r.border_color)]) > 1:
                    raise ValidationError(_('Color must be unique per connector.'))

    def del_and_recreate_image_chat(self):
        Product = self.env['product.product'].sudo()
        prod_ids = Product.search([('image_chat', '!=', False)])
        prod_ids.write({'image_chat': False})
        Product._recreate_image_chat()

    @api.model
    def execute_maintenance(self, days=21):
        ''' Call from cron.
            Delete attachment older than N days. '''
        Message = self.env['acrux.chat.message']
        date_old = datetime.now() - timedelta(days=int(days))
        date_old = date_old.strftime(DEFAULT_SERVER_DATE_FORMAT)
        mess_ids = Message.search([('res_model', '=', 'ir.attachment'),
                                   ('res_id', '!=', False),
                                   ('date_message', '<', date_old)])
        attach_to_del = mess_ids.mapped('res_id')
        erased_ids = Message.unlink_attachment(attach_to_del)
        for mess_id in mess_ids:
            if mess_id.res_id in erased_ids:
                text = '%s\n(Attachment removed)' % mess_id.text
                mess_ids.write({'text': text.strip(),
                                'res_id': False})
        _logger.info('________ | execute_maintenance: Deleting %s attachments older than %s' %
                     (len(attach_to_del), date_old))
