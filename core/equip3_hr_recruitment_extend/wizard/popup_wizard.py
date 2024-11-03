from typing import Sequence
from odoo import fields,models,api,_
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from ...equip3_general_features.models.approval_matrix import approvalMatrixWizard

class equp3ManpowerPopupWizard(models.TransientModel):
    _name = 'manpower.approve.wizard'
    feedback = fields.Text()
    requisition_id = fields.Many2one('manpower.requisition')
    state = fields.Char()
    
    
    def submit(self):
        sequence = """record.requisition_id.approval_matrix_ids"""
        sequence_apply = """record.requisition_id.approval_matrix_ids.filtered(lambda  line:len(line.approver_confirm) != line.minimum_approver)"""
        approval = """record.requisition_id.approval_matrix_ids.filtered(lambda  line:record.env.user.id in line.approver_id.ids and len(line.approver_confirm) != line.minimum_approver and  line.sequence == min_seq)"""
        approval_matrix_wizard = approvalMatrixWizard(self,sequence,sequence_apply,approval)
        status = approval_matrix_wizard.submit(self.requisition_id,{'state':'approved'},{'state':'rejected'})
        if status:
            self.requisition_id.job_id.is_published = True
        
            
            
            
            
    