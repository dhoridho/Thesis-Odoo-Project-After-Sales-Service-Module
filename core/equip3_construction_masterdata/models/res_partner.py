# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(string="Is a customer")
    is_a_vendor = fields.Boolean(string="Is a Vendor")
    is_sub_contractor = fields.Boolean(string="Is Sub Contractor")
    document_ids = fields.One2many('document.document', 'partner_id', string="Documents")
    vendor_type = fields.Selection([
        ('vendor', 'Vendor'),
        ('sub_contractor', 'Sub Contractor'),
    ], 'Vendor Type')
    company_id = fields.Many2one('res.company')
    is_project_location = fields.Boolean('Is Project Location', default=False)

    @api.model
    def create(self, vals):
        if vals.get('is_sub_contractor', True):
            vals.update({'vendor_type': 'sub_contractor'})
        else:
            vals.update({'vendor_type': 'vendor'})
        res = super(ResPartner, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('is_sub_contractor', True):
            vals.update({'vendor_type': 'sub_contractor'})
        else:
            vals.update({'vendor_type': 'vendor'})
        res = super(ResPartner, self).write(vals)
        return res


class Documents(models.Model):
    _name = "document.document"
    _description = "Document Details"

    partner_id = fields.Many2one("res.partner")
    document_type = fields.Selection([
        ('mandatory', 'Mandatory'),
        ('additional', 'Additional'),
    ], 'Document', required=True)
    description = fields.Text(string="Description")
    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date", required=True)
    status = fields.Selection([
        ('expired', 'Expired'),
        ('persisted', 'Persisted'),
    ], 'Status')
    date_published = fields.Datetime(string="Date Published", readonly=True, default=lambda self: fields.Datetime.now())
    document_upload = fields.Binary("Upload Document")
    document_name = fields.Char('Upload Your Document')
