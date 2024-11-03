from odoo import fields, models, api, _
from lxml import etree

class field_conditional_access(models.Model):
    _name = 'field.conditional.access'
    _description = "Fields Conditional Access"

    access_management_id = fields.Many2one('access.management', 'Access Management')
    model_id = fields.Many2one('ir.model', 'Model')
    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)
    attrs_field_id = fields.Many2one('ir.model.fields', 'Attrs Field')
    domain_field_id = fields.Many2one('ir.model.fields', 'Domain Field')
    domain_field_relation = fields.Char(related='domain_field_id.relation', readonly=True, store=True)

    attrs_type = fields.Selection([('invisible','Invisible'),('readonly','Read-Only'),('required','Required')],
                                  default='invisible')
    
    field_attrs = fields.Char(help="Make selected fields read only, invisible, or required based on another field in selected model from the defined users")
    field_domain = fields.Char(default='[]')

    apply_attrs = fields.Boolean('Apply Attrs')
    apply_field_domain = fields.Boolean('Apply Domain')

    


    
