from odoo import fields, models,_,api
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning



class RevisedBOMWizard(models.TransientModel):
    _name = "revised.bom.wizard"
    _description = "Revised BOM Wizard"
    
    bom_id = fields.Many2one('mrp.bom')
    bom_revised_type = fields.Selection([('minor','Minor'),
                                         ('major','Major')],string='Revision Type',default='minor',copy=False)
    minor_next_version = fields.Float('Next Minor Version')
    major_next_version = fields.Float('Next Major Version')
    
    @api.onchange('bom_revised_type')
    def onchange_next_version(self):
        if self.bom_id:
            if self.bom_revised_type == 'minor':
                if self.env.context.get('for_new_revised'):
                    prev_name = self.bom_id.revision_name
                    new_revision_name = prev_name + 0.001
                    self.minor_next_version = new_revision_name
                if self.env.context.get('for_restore_revised'):
                    prev_name = self.bom_id.current_revision_id.revision_name
                    new_revision_name = prev_name + 0.001
                    self.minor_next_version = new_revision_name
            if self.bom_revised_type == 'major':
                if self.env.context.get('for_new_revised'):
                    prev_name = self.bom_id.revision_name
                    new_revision_name = int(prev_name) + 1.000
                    self.major_next_version = new_revision_name
                if self.env.context.get('for_restore_revised'):
                    prev_name = self.bom_id.current_revision_id.revision_name
                    new_revision_name = int(prev_name) + 1.000
                    self.major_next_version = new_revision_name
    
    def action_confirm(self):
        if self.bom_id:
            if self.env.context.get('for_new_revised'):
                if self.bom_revised_type == 'minor':
                    self.bom_id.with_context(revised_for_minor=True,for_new_revised=True).create_revised()
                if self.bom_revised_type == 'major':
                    self.bom_id.with_context(revised_for_major=True,for_new_revised=True).create_revised()
            if self.env.context.get('for_restore_revised'):
                if self.bom_revised_type == 'minor':
                    # self.bom_id.current_revision_id.with_context(revised_for_minor=True,for_restore_revised=True).create_revised()
                    self.bom_id.with_context(revised_for_minor=True,for_restore_revised=True).create_revised()
                if self.bom_revised_type == 'major':
                    # self.bom_id.current_revision_id.with_context(revised_for_major=True,for_restore_revised=True).create_revised()
                    self.bom_id.with_context(revised_for_major=True,for_restore_revised=True).create_revised()
    