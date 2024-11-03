from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json


class QiscusTemplate(models.Model):
    _name = 'qiscus.template'
    _description = "Qiscus Template"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    namespace = fields.Char('Namespace')
    qiscus_template_id = fields.Integer('Template ID')
    content_ids = fields.One2many('qiscus.template.content', 'template_id', string='Content IDs')
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', ondelete='cascade')


    def ir_cron_syncronize_template(self):
        app_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid')
        channel_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id')
        payload = {'email': 'Saepi.Ridwan@hashmicro.com.sg',
                   'password': 'AdminHM123456#'

                   }
        auth_user = requests.post(f'https://multichannel.qiscus.com/api/v1/auth', data=payload, verify=True)
        response_data_auth = json.loads(auth_user.content)
        header = {'Qiscus-App-Id': app_id,
                  'Authorization': response_data_auth['data']['user']['authentication_token']}
        param = {'approved': True,
                 'limit': 1000,
                 'channel_id': channel_id}
        get_template_qiscus = requests.get(f'https://multichannel.qiscus.com/api/v2/admin/hsm', headers=header,
                                           params=param, verify=True)
        response_data = json.loads(get_template_qiscus.content)
        if response_data['data']['hsm_templates']:
            ids = [data['id'] for data in response_data['data']['hsm_templates']]
            qiscus_template_to_delete = self.sudo().search([('qiscus_template_id', 'not in', ids)])
            if qiscus_template_to_delete:
                for unlink_data in qiscus_template_to_delete:
                    unlink_data.unlink()

            for data in response_data['data']['hsm_templates']:
                qiscus_template = self.sudo().search([('qiscus_template_id', '=', int(data['id']))])
                if not qiscus_template:
                    line_ids = []
                    template_to_create = self.sudo().create(
                        {'qiscus_template_id': int(data['id']), 'name': data['name'], 'namespace': data['namespace']})
                    for line in data['hsm_details']:
                        header = f"{line['header_default_value']}\n" if line['header_default_value'] else ''
                        header_content = f"{line['header_content']}\n" if line['header_content'] else ''
                        footer_content = f"{line['footer']}\n" if line['footer'] else ''
                        line_ids.append((0, 0, {'language': line['language'],
                                                'content': f"""{header}{header_content}{line['content']}\n{footer_content}""",
                                                'content_id': line['id'],
                                                }))
                    template_to_create.content_ids = line_ids
                if qiscus_template:
                    qiscus_template.qiscus_template_id = int(data['id'])
                    qiscus_template.name = data['name']
                    qiscus_template.namespace = data['namespace']
                    for line in data['hsm_details']:
                        line_ids = []
                        qiscus_template_content = self.env['qiscus.template.content'].sudo().search(
                            [('template_id', '=', qiscus_template.id), ('content_id', '=', line['id'])])
                        header = f"{line['header_default_value']}\n" if line['header_default_value'] else ''
                        header_content = f"{line['header_content']}\n" if line['header_content'] else ''
                        footer_content = f"{line['footer']}\n" if line['footer'] else ''
                        if qiscus_template_content:
                            qiscus_template_content.language = line['language']
                            qiscus_template_content.content = f"""{header}{header_content}{line['content']}\n{footer_content}"""
                        else:
                            line_ids.append((0, 0, {'content_id': line['id'],
                                                    'language': line['language'],
                                                    'content': f"""{header}{header_content}{line['content']}\n{footer_content}"""
                                                    }))
                            qiscus_template.content_ids = line_ids
                    ids_to_delete = [data_delete['id'] for data_delete in data['hsm_details']]
                    qiscus_template_content_delete = self.env['qiscus.template.content'].sudo().search(
                        [('template_id', '=', qiscus_template.id), ('content_id', 'not in', ids_to_delete)])
                    if qiscus_template_content_delete:
                        for delete in qiscus_template_content_delete:
                            delete.unlink()


class QiscusTemplateContent(models.Model):
    _name = 'qiscus.template.content'
    _description = "Qiscus Template Content"
    _rec_name = 'name'

    template_id = fields.Many2one('qiscus.template', string='Template ID', ondelete='cascade')
    name = fields.Char('Name', compute='_compute_name')
    language = fields.Char('Language')
    content_id = fields.Integer('Content ID')
    content = fields.Text('Content')

    @api.depends('template_id', 'language')
    def _compute_name(self):
        for record in self:
            if record.template_id and record.language:
                record.name = f"{record.template_id.name} - {record.language}"

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} - {}".format(record.template_id.name, record.language)))
        return result