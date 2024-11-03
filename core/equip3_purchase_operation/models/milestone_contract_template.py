from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class MilestoneContractTemplate(models.Model):
    _name = 'milestone.contract.template'
    _description = 'Milestone Contract Term Template'

    name = fields.Char(string='Name', required=True)
    checklist_template_id = fields.Many2one(comodel_name='purchase.custom.checklist.template', string='Checklist Template', domain="[('order','=','milestone')]")
    line_ids = fields.One2many(comodel_name='milestone.contract.template.line', inverse_name='template_id', string='Milestone Line')
    checklist_ids = fields.One2many(comodel_name='milestone.contract.template.checklist', inverse_name='template_id', string='Checklist Line')
    

    @api.onchange('checklist_template_id')
    def _onchange_checklist_template_id(self):
        if self.checklist_template_id:
            checklist_ids = []
            for checklist in self.checklist_template_id.checklist_template:
                vals = {
                    'name':checklist.name,
                    'desc':checklist.description
                }
                checklist_ids.append((0,0,vals))
            self.checklist_ids.unlink()
            self.checklist_ids = checklist_ids
        else:
            self.checklist_ids.unlink()
        
    @api.constrains('line_ids')
    def _check_line_ids_contract_term(self):
        for req in self:
            total = 0
            if req.line_ids:
                for i in req.line_ids:
                    if i.contract_term < 0:
                        raise ValidationError('Please Input valid amount for Contract Terms')
                    total += i.contract_term
            if total != 100:
                raise ValidationError('Total contract terms should be 100%')

class MilestoneContractTemplateLine(models.Model):
    _name = 'milestone.contract.template.line'
    _description = 'Details Milestone Contract Term Template'

    template_id = fields.Many2one(comodel_name='milestone.contract.template', string='Template',ondelete="cascade")
    checklist_template_id = fields.Many2one(comodel_name='purchase.custom.checklist.template', string='Checklist Template', domain="[('order','=','milestone')]")
    name = fields.Char(string='Milestone Name', required=True)
    contract_term = fields.Float(string='Contract Terms (%)')

class MilestoneContractTemplateChecklist(models.Model):
    _name = 'milestone.contract.template.checklist'
    _description = 'Checklist Milestone Contract Term Template'

    template_id = fields.Many2one(comodel_name='milestone.contract.template', string='Template',ondelete="cascade")
    name = fields.Char(string='Name', required=True)
    desc = fields.Char(string='Description')
    