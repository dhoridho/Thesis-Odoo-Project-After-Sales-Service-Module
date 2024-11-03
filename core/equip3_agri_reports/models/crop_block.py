from odoo import models


class AgricultureCropBlock(models.Model):
    _inherit = 'crop.block'

    def _get_action(self, action_xmlid):
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['division_id'] = self.division_id.id
        context = {
            'search_default_block_id': [self.id],
            'default_block_id': self.id,
            'default_division_id': self.division_id.id,
        }
        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        return action
    
    def get_action_activity_available(self):
        return self._get_action('equip3_agri_reports.agriculture_daily_activity_available_action')
    
    def get_action_activity_draft(self):
        return self._get_action('equip3_agri_reports.agriculture_daily_activity_draft_action')
    
    def get_action_activity_progress(self):
        return self._get_action('equip3_agri_reports.agriculture_daily_activity_progress_action')
