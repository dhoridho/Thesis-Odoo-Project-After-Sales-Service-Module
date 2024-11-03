# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import requests


class IZIAnalysis(models.Model):
    _inherit = 'izi.analysis'

    method = fields.Selection(
        selection_add=[
            ('model', 'Model'),
        ])


    def action_get_lab_analysis_text(self, ai_analysis_data):
        result = {
            'status': 200,
            'ai_analysis_text': self.ai_analysis_text,
        }
        izi_lab_url = self.env['ir.config_parameter'].sudo().get_param('izi_lab_url')
        if not izi_lab_url:
            raise UserError(_('Please set AI API Key in System Parameters.'))
        analysis_name = self.name
        visual_type_name = self.visual_type_id.name
        try:
            res = requests.post('''%s/lab/analysis/description''' % (izi_lab_url), json={
                'izi_lab_api_key': self.env.company.izi_lab_api_key,
                'analysis_name': analysis_name,
                'visual_type_name': visual_type_name,
                'data': ai_analysis_data,
            }, timeout=120)
            res = res.json()
            if res.get('result') and res.get('result').get('status') == 200 and res.get('result').get('description'):
                description = res.get('result').get('description')
                self.ai_analysis_text = description
            elif res.get('result') and res.get('result').get('status') and res.get('result').get('status') != 200:
                result = {
                    'status': res.get('result').get('status'),
                    'message': res.get('result').get('message') or '',
                }
        except Exception as e:
            pass
        result['ai_analysis_text'] = self.ai_analysis_text
        return result


    def action_get_lab_script(self, instruction):
        result = {
            'status': 200,
            'code': '',
        }
        izi_lab_url = self.env['ir.config_parameter'].sudo().get_param('izi_lab_url')
        if not izi_lab_url:
            raise UserError(_('Please set AI API Key in System Parameters.'))
        try:
            res = requests.post('''%s/lab/analysis/script''' % (izi_lab_url), json={
                'izi_lab_api_key': self.env.company.izi_lab_api_key,
                'instruction': instruction,
            }, timeout=120)
            res = res.json()
            if res.get('result') and res.get('result').get('status') == 200 and res.get('result').get('code'):
                code = res.get('result').get('code')
                result['code'] = code
            elif res.get('result') and res.get('result').get('status') and res.get('result').get('status') != 200:
                result = {
                    'status': res.get('result').get('status'),
                    'message': res.get('result').get('message') or '',
                }
        except Exception as e:
            result = {
                'status': 400,
                'message': str(e),
            }
        return result


class IZIAnalysisVisualConfig(models.Model):
    _inherit = 'izi.analysis.visual.config'
    _description = 'Hashmicro Analysis Visual Config'