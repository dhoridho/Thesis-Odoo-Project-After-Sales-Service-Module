# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

class DocumentDirectory(models.Model):
    _name = "document.directory"
    _description = "Document Directory"

    def _get_attachment_count(self):
        res = {}
        AttachmentObj = self.env['ir.attachment']
        for rec in self:
            attchement_count = 0
            if rec.res_model and rec.res_model.name:
                attchement_count = AttachmentObj.search_count([
                    ('res_model', 'in', [rec.res_model.model])])
            rec.attchement_count = attchement_count

    name = fields.Char(required=True)
    parent_id = fields.Many2one('document.directory',string='Parent Directory', index=True, ondelete='cascade')
    children_ids = fields.One2many('document.directory', 'parent_id', string='Children', copy=True)
    user_ids = fields.Many2many('res.users', 'document_user_rel', 'user_id', 'doc_id', string="Users")
    description = fields.Text(string='Description')
    tag_ids = fields.Many2many('document.tag', 'directory_tag_rel', 'directory_id', 'tag_id', 
        string='Tags', help="Classify and analyze your Document")
    department_id = fields.Many2one('hr.department', string='Department', ondelete='restrict')
    attchement_count = fields.Integer(compute='_get_attachment_count', string="Number of documents attached")
    res_model = fields.Many2one('ir.model', 'Model', ondelete='cascade')

    @api.constrains('res_model')
    def _check_model(self):
        if self.res_model:
            directories = self.search([('id', '!=', self.id),('res_model', '=',self.res_model.id)])
            if directories:
                raise ValidationError(_('You can have only one directory for a model.'))
     
    def action_view_attachments(self):
        attachments = self.env['ir.attachment'].search([('res_model', 'in', [self.res_model.model])])
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_attachment")
        action['domain'] = [('id', 'in', attachments.ids)]
        action['context'] = {
                'default_res_model': self.res_model.model,
                'default_directory_id': self.id,
                'default_is_document': True}
        return action


    def name_get(self):
        def get_names(directory):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = []
            while directory:
                res.append(directory.name)
                directory = directory.parent_id
            return res
        return [(directory.id, " / ".join(reversed(get_names(directory)))) for directory in self]

    @api.constrains('parent_id')
    def _check_directory_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive Directory.'))
        return True


class Attachment(models.Model):
    _inherit = "ir.attachment"

    is_document = fields.Boolean("Is Document")
    directory_id = fields.Many2one('document.directory', string='Directory', ondelete='restrict')
    description = fields.Text(string='Description')
    tag_ids = fields.Many2many('document.tag', 'hms_document_tag_rel', 'document_id', 'tag_id', 
        string='Tags', help="Classify and analyze your Document")


class Tag(models.Model):
    _name = "document.tag"
    _description = "Document Tags"

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: