from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class SectionLine(models.Model):
    _name = "section.line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Section"
    _rec_name = 'complete_name'
    _order = 'complete_name'

    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string="Code", tracking=True)
    name = fields.Char(string="Section", tracking=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    cons_use_code = fields.Boolean('Use Code', compute='_compute_use_code', store=False)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    project_id = fields.Many2one('project.project', string='Project')

    @api.depends('name')
    def _compute_use_code(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        cons_use_code = IrConfigParam.get_param('cons_use_code')
        for record in self:
            record.cons_use_code = cons_use_code

    @api.depends('code', 'name', 'cons_use_code')
    def _compute_complete_name(self):
        for res in self:
            if res.cons_use_code == True:
                if res.code and res.name:
                    res.complete_name = '%s - %s' % (res.code, res.name)
                else:
                    if not res.name:
                        res.name = '%s' % (res.complete_name)
            else:
                if res.name:
                    res.complete_name = '%s' % (res.name)
                else:
                    res.name = '%s' % (res.complete_name)
    
    @api.constrains('code')
    def _check_existing_code(self):
        for record in self:
            code_id = self.env['section.line'].search(
                [('code', '=', record.code)])
            if record.cons_use_code == True:
                if len(code_id) > 1:
                    for res in code_id:
                        raise ValidationError((_("The code already exists with section '{}', so please change the code.".format(res.name))))
            else:
                pass
    
    @api.constrains('name')
    def _check_existing_name(self):
        for record in self:
            name_id = self.env['section.line'].search(
                [('name', '=', record.name)])
            if record.cons_use_code == True:
                if len(name_id) > 1:
                    for res in name_id:
                        raise ValidationError(_("The name of this section already exists with code '{}', so please change the name.".format(res.code)))
            else:
                if len(name_id) > 1:
                    for res in name_id:
                        raise ValidationError(_("The name of this section already exists, so please change the name."))

