from multiprocessing import active_children
from odoo import models, api


class QualityAlerInherit(models.TransientModel):
    _inherit = 'sh.qc.alert'
    
    def action_validate(self):
        res = super(QualityAlerInherit, self).action_validate()
        active_id = self.env.context.get('active_id', False)
        quality_obj = self.env['sh.quality.alert'].search([('piking_id', '=', active_id)])
        if quality_obj:
            quality_obj.create_qc_alert()
        return res
