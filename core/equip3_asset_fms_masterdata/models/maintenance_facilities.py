# -*- coding: utf-8 -*-
import logging
import re
from io import BytesIO
import base64
import qrcode

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)



class modultab(models.Model):
    _name = 'equip3_asset_fms_masterdata_tab'
    _description = 'Modul Tab'

class modulasseet(models.Model):
    _name = 'equip3_asset_fms_masterdata'
    _description = 'Modul Asset'

class facilitiesarea(models.Model):
    _name = 'maintenance.facilities.area'
    _description = 'Modul Facilities Area'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = "parent_location"
    _order = 'comp_name, id'
    _rec_name = 'comp_name'
    _check_company_auto = True
    
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'The name must be unique per company!'),
    ]

    name = fields.Char('Category Name', required=True, translate=True, copy=False)
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id)

    parent_location = fields.Many2one(
        'maintenance.facilities.area', 'Parent Location', index=True, ondelete='cascade', check_company=True,
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    
    child_ids = fields.One2many('maintenance.facilities.area', 'parent_location', 'Contains')
    note = fields.Text('Internal Notes')

    branch = fields.Many2one(
        "res.branch",
        string="Branch",
        default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        tracking=True,
        required=True,
    )
    assets_ids = fields.Many2many('maintenance.equipment', string="Assets", compute="get_all_asset_qr")
    maintenance_ids_f = fields.One2many(
        "maintenance.equipment", "maintenance_f_id", string="Maintenance Asset"
    )
    
    maintenance_ids_f2 = fields.One2many(
        "maintenance.plan", "maintenance_p_id", string="Maintenance Plan"
    )

    comp_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)

    request_count2 = fields.Integer(string='Requests Count', compute='_compute_request_count')

    # wo_count = fields.Integer(string='Work Order Count', compute='_compute_wo_count')
    wo_count  = fields.Integer(string='# of Work Order', compute='_compute_work_order_count', readonly=True)
    wo = fields.Integer (string="Work Order")

    maintenance_plan_count2 = fields.Integer(
        compute="_compute_maintenance_plan_count",
        string="Preventive Maintenance Plan Count",
    )
    maintenance_plan_count3 = fields.Integer(
        compute="_compute_maintenance_plan_count2",
        string="Hour Meter Maintenance Plan Count",
    )
    maintenance_plan_count4 = fields.Integer(
        compute="_compute_maintenance_plan_count3",
        string="Odometer Maintenance Plan Count",
    )

    asset_count = fields.Integer(string='Asset', compute='_compute_asset_count')
    qrcode = fields.Binary("QR Code", attachment=True, store=True)
    rentable_area = fields.Boolean(string='Rentable Area', default=False)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Facilities Area'),
            'template': '/equip3_asset_fms_masterdata/static/xls/facilities_area_template.xls'
        }]

    def _compute_request_count(self):
        for rec in self:
            request_count2 = self.env['maintenance.request'].search_count([('facility', '=', rec.id)])
            rec.request_count2 = request_count2

    def _compute_maintenance_plan_count(self):
        for rec in self:
            maintenance_plan_count2 = self.env['maintenance.plan'].search_count([('facility_area', '=', rec.id), ('is_preventive_m_plan', '=', True)])
            rec.maintenance_plan_count2 = maintenance_plan_count2

    def _compute_maintenance_plan_count2(self):
        for rec in self:
            maintenance_plan_count3 = self.env['maintenance.plan'].search_count([('facility_area', '=', rec.id), ('is_hourmeter_m_plan', '=', True)])
            rec.maintenance_plan_count3 = maintenance_plan_count3

    def _compute_maintenance_plan_count3(self):
        for rec in self:
            maintenance_plan_count4 = self.env['maintenance.plan'].search_count([('facility_area', '=', rec.id), ('is_odometer_m_plan', '=', True)])
            rec.maintenance_plan_count4 = maintenance_plan_count4

    def _compute_asset_count(self):
        for rec in self:
            asset_count = self.env['maintenance.equipment'].search_count([('fac_area', '=', rec.id)])
            rec.asset_count = asset_count

    @api.depends('name', 'parent_location.comp_name')
    def _compute_complete_name(self):
        for location in self:
            if location.parent_location:
                location.comp_name = '%s / %s' % (location.parent_location.comp_name, location.name)
            else:
                location.comp_name = location.name

    @api.constrains('parent_location')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))
        return True
    
    def _compute_work_order_count(self):
        work_order_obj = self.env['maintenance.work.order']
        work_order_ids = work_order_obj.search([('facility','=', self.id)])
        for book in self:
            book.update({
                'wo_count' : len(work_order_ids)
                })

    def wo_action_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Work Order',
            'res_model': 'maintenance.work.order',
            'domain': [('facility','=',self.id)]}

    @api.model
    def create(self, vals):
        result = super().create(vals)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/page/maintenance_request/?facility_area=%d'%(result.id)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(base_url)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        result.qrcode = qr_image
        return result

    def get_all_asset_qr(self):
        for rec in self:
            assets = self.env['maintenance.equipment'].search([('fac_area', '=', rec.id)])
            self.assets_ids = assets