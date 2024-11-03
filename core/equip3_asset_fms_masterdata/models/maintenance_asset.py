# -*- coding: utf-8 -*-
import base64
from io import BytesIO
from datetime import date, datetime, timedelta
import qrcode
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from re import findall as regex_findall
from re import split as regex_split
from urllib.parse import urlparse
import json

class modulequip(models.Model):
    _inherit = 'maintenance.equipment'

    qr_code = fields.Binary("QR Code", attachment=True, store=True)
    category_id = fields.Many2one(string='Asset Category', required=True)
    owner = fields.Many2one('res.partner', string='Owner', tracking=True)
    held_by_id = fields.Many2one(comodel_name='res.partner', string='Held By', tracking=True)
    company_id_asset = fields.Many2one('res.partner', string='Company Owner')
    maintenance_teams_id = fields.Many2one('maintenance.teams', string='Assigned To', ondelete='restrict')
    fac_area = fields.Many2one('maintenance.facilities.area', string='Facilities Area', tracking=True)
    maintenance_hm = fields.One2many('maintenance.hour.meter', 'maintenance_asset', string='Hour Meter')
    scrap_date = fields.Date(string='Scrap Date')
    purchase_value = fields.Float(string='Purchase Value')
    active = fields.Boolean(default=True)
    state = fields.Selection([('operative','Operative'), ('missing','Missing'), ('breakdown','Breakdown'),('maintenance','Maintenance'), ('scrapped','Scrapped'), ('sold', 'Sold')], default="operative", string="Status")
    work_order = fields.Integer(string="Work Order")
    repair = fields.Integer (string="Repair")
    maintenance_f_id = fields.Many2one(string="Maintenance Facilities Area", comodel_name="maintenance.facilities.area", ondelete="restrict")
    hm_count = fields.Integer(string='Hour Meter Count', compute='_compute_hm_count')
    wo_count  = fields.Integer(string='Work Order Count', compute='_compute_work_order_count', readonly=True)
    repair_count = fields.Integer(string='Repair Count', compute='_compute_repair_count')
    request_count = fields.Integer(string='Requests Count', compute='_compute_request_count')
    odometer_mp_count = fields.Integer(string="Odometer Plans", compute='_compute_plan_count')
    odometer_mp_ids = fields.Many2many('maintenance.plan', compute="_compute_plan_count")
    hourmeter_mp_count = fields.Integer(string="Hourmeter Plans", compute='_compute_plan_count')
    hourmeter_mp_ids = fields.Many2many('maintenance.plan', compute="_compute_plan_count")
    preventive_mp_count = fields.Integer(string="Preventive Plans", compute='_compute_plan_count')
    preventive_mp_ids = fields.Many2many('maintenance.plan', compute="_compute_plan_count")
    am_count = fields.Integer(string='Asset Moves Count', compute='_compute_am_count', readonly=True)
    account_asset_id = fields.Many2one('account.asset.asset', string="Account Asset")
    vehicle_parts_ids = fields.One2many('vehicle.parts', 'maintenance_equipment_id', string='Parts')
    missing = fields.Selection([('yes','Yes'), ('no','No')],string="Missing")
    missing_date = fields.Date(string='Missing Date', readonly=True, compute='_compute_missing_date')
    branch_id = fields.Many2one(
        "res.branch",
        string="Branch",
        default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        tracking=True,
        required=True,
    )
    barcode = fields.Char(string='Barcode')
    important_documents_line = fields.One2many('important.document.line', 'equipment_id', string='Important Documents', tracking=True)
    asset_value = fields.Float(string='Asset Value')
    sale_at = fields.Date(string='Sale At')
    scrapped_at = fields.Date(string='Scrapped At')
    asset_code = fields.Char(string='Asset Code')
    owner_user_id = fields.Many2one(compute='_compute_owner', store=True, string="Owner User")
    total_expired_document = fields.Integer(string='Total Expired Document', compute='_compute_total_expired_documents')
    expired_type = fields.Selection(string='Expired', selection=[('expired', 'Expired'), ('soon', 'Expired Soon'), ('both', 'Both')], compute='_compute_total_expired_documents')

    asset_prefix = fields.Char(string="Asset Prefix", size=10)
    is_generate_product = fields.Boolean(related='category_id.autogenerate_asset')
    category_prefix_preference = fields.Selection(related='category_id.category_prefix_preference')
    product_template_id = fields.Many2one('product.template', string="Product", domain=[('type', '=', 'asset')], required=True, readonly=False)
    
    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        if self.product_template_id:
            self.category_id = self.product_template_id.asset_control_category.id

    @api.onchange('vehicle_parts_ids')
    def _onchange_vehicle_parts_ids(self):
        selected_equipment_ids = self.vehicle_parts_ids.mapped('equipment_id.id')

        for line in self.vehicle_parts_ids:
            available_equipments = [('id', 'not in', selected_equipment_ids)]
            line.equipment_id_domain = json.dumps(available_equipments)

    def missing_asset(self):
        for rec in self:
            rec.write({'state' : 'missing'})
            rec.write({'missing' : 'yes'})

    def operate_asset_from_missing(self):
        for rec in self:
            rec.write({'state' : 'operative'})
            rec.write({'missing' : 'no'})

    @api.onchange('category_id', 'asset_prefix')
    def _onchange_product_categ_id(self):
        name = ''
        if self.asset_prefix and self.category_id and \
            self.category_id.category_prefix_preference and \
            self.category_id.current_sequence and \
            self.category_id.autogenerate_asset and \
            self.category_id.category_prefix_preference == 'additional':
            prefix_cont = ""
            if self.category_id.asset_prefix:
                prefix_cont = str(self.category_id.asset_prefix)
            name = prefix_cont + "-" + self.category_id.current_sequence
            self.asset_code = name
        elif self.category_id and \
            self.category_id.autogenerate_asset and \
            self.category_id.category_prefix_preference == 'all':
            if self.category_id.category_prefix_preference and self.category_id.current_sequence:
                prefix_str = ""
                if self.category_id.asset_prefix:
                    prefix_str = str(self.category_id.asset_prefix)
                name = prefix_str + "-" + self.category_id.current_sequence
                self.asset_code = name
            else:
                pass
        else:
            self.asset_code = ""

    # @api.model
    # def create(self, vals):
    #     print('createeeeeeeeeeeeeeeeeeeeeee')
    #     maintenance_equip = super(modulequip, self).create(vals)
    #     for equip in maintenance_equip:
    #         if equip.is_generate_product and \
    #             not equip.product_prefix:
    #             name = ''
    #             if equip.product_prefix:
    #                 name = equip.product_prefix
    #             equip.product_prefix = name
    #             equip._onchange_product_categ_id()
    #             next_serial = equip.category_id.current_sequence
    #             caught_initial_number = regex_findall("\d+", next_serial)
    #             initial_number = caught_initial_number[-1]
    #             padding = len(initial_number)
    #             # We split the serial number to get the prefix and suffix.
    #             splitted = regex_split(initial_number, next_serial)
    #             # initial_number could appear several times in the SN, e.g. BAV023B00001S00001
    #             prefix = initial_number.join(splitted[:-1])
    #             suffix = splitted[-1]
    #             initial_number = int(initial_number)

    #             lot_names = []
    #             for i in range(0, 2):
    #                 lot_names.append('%s%s%s' % (
    #                     prefix,
    #                     str(initial_number + i).zfill(padding),
    #                     suffix
    #                 ))
    #             next_serial_number = lot_names[-1]
    #             equip.category_id.current_sequence = next_serial_number
    #     return maintenance_equip


    @api.depends('employee_id', 'department_id', 'equipment_assign_to')
    def _compute_owner(self):
        for equipment in self:
            equipment.owner_user_id = self.env.user.id
            if equipment.equipment_assign_to == 'employee':
                equipment.owner_user_id = equipment.employee_id.user_id.id
            elif equipment.equipment_assign_to == 'department':
                equipment.owner_user_id = equipment.department_id.manager_id.user_id.id

    @api.onchange('missing', 'missing_date')
    def onchange_missing_date(self):
        if self.missing == 'yes' :
            self.missing_date = datetime.today()
        else:
            self.missing_date = ''

    def _compute_missing_date(self):
        if self.missing == 'yes' :
            self.missing_date = datetime.today()
        else:
            self.missing_date = ''

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Assets/Vehicles'),
            'template': '/equip3_asset_fms_masterdata/static/xls/asset_vehicle_template.xls'
        }]


    @api.model
    def create(self, vals):
        result = super().create(vals)

        barcode = self.env['ir.sequence'].next_by_code('maintenance.equipment.barcode.sequence')
        result.barcode = barcode

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        parsed_url = urlparse(base_url)
        base_url = f'{parsed_url.netloc}/page/asset_information/?asset={result.id}'

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
        result.qr_code = qr_image

        for equip in result:
            # if equip.is_generate_product and not equip.asset_prefix:
            if equip.is_generate_product:
                name = ''
                if equip.asset_prefix:
                    name = equip.asset_prefix
                equip.asset_prefix = name
                equip._onchange_product_categ_id()
                next_serial = equip.category_id.current_sequence
                caught_initial_number = regex_findall("\d+", next_serial)
                initial_number = caught_initial_number[-1]
                padding = len(initial_number)
                splitted = regex_split(initial_number, next_serial)
                prefix = initial_number.join(splitted[:-1])
                suffix = splitted[-1]
                initial_number = int(initial_number)

                lot_names = []
                for i in range(0, 2):
                    lot_names.append('%s%s%s' % (
                        prefix,
                        str(initial_number + i).zfill(padding),
                        suffix
                    ))
                next_serial_number = lot_names[-1]
                equip.category_id.current_sequence = next_serial_number
        return result

    def name_get(self):
        res = super(modulequip, self).name_get()
        result = []
        for record in self:
            name = record.name
            if record.serial_no:
                name += ' ' + '[' + record.serial_no + ']'
            result.append((record.id, name))
        return result

    def create_account_asset(self):
        category_id = self.env['account.asset.category'].search([('type', '=', 'purchase')], limit=1)
        vals = {
            'name' : self.name,
            'company_id' : self.company_id.id,
            'date' : date.today(),
            'first_depreciation_manual_date' : date.today(),
            'equipment_id' : self.id,
            'value' : self.asset_value,
            'branch_id' : self.branch_id.id,
        }
        if category_id:
            vals['category_id'] = category_id.id
        context = self._context        
        if context.get('active_model') == 'stock.picking':
            picking_id = self.env['stock.picking'].browse(context.get('active_ids'))
            vals['po_ref'] = picking_id.origin
            vals['analytic_tag_ids'] = picking_id.analytic_account_group_ids
        asset_id = self.env['account.asset.asset'].create(vals)
        self.account_asset_id = asset_id.id

    def action_account_asset(self):
        context = dict(self.env.context) or {}
        context.update({'default_equipment_id': self.id})
        return{
            'type': 'ir.actions.act_window',
            'view_type' : 'form',
            'view_mode' : 'form',
            'res_model': 'account.asset.asset',
            'target': 'current',
            'context': context,
            'res_id': self.account_asset_id.id,
        }

    def breakdown_action(self):
        self.write({'state': 'breakdown'})

    def scrapped_action(self):
        self.write({'state': 'scrapped'})

    def _compute_plan_count(self):
        plan_data = self.env['maintenance.plan'].search([])
        self.odometer_mp_count = None
        self.odometer_mp_ids = None
        self.hourmeter_mp_count = None
        self.hourmeter_mp_ids = None
        self.preventive_mp_count = None
        self.preventive_mp_ids = None
        eq_id = None
        odometer_mps = None
        odometer_mps_lst = []
        hourmeter_mps = None
        hourmeter_mps_lst = []
        prev_mps = None
        prev_mps_lst = []
        for rec in self:
            for plan in plan_data:
                if plan.is_odometer_m_plan:
                    odometer_mps = plan.filtered(lambda odo: rec.category_id in odo.maintenance_category_ids)
                    if not odometer_mps:
                        for eq_id in plan.task_check_list_ids:
                            if eq_id.equipment_id.id == rec.id:
                                odometer_mps = plan
                    if odometer_mps:
                        odometer_mps_lst.append(odometer_mps.id)
                if plan.is_hourmeter_m_plan:
                    hourmeter_mps = plan.filtered(lambda odo: rec.category_id in odo.maintenance_category_ids)
                    if not hourmeter_mps:
                        for eq_id in plan.task_check_list_ids:
                            if eq_id.equipment_id.id == rec.id:
                                hourmeter_mps += plan
                    if hourmeter_mps:
                        hourmeter_mps_lst.append(hourmeter_mps.id)
                if plan.is_preventive_m_plan:
                    prev_mps = plan.filtered(lambda odo: rec.category_id in odo.maintenance_category_ids)
                    if not prev_mps:
                        for eq_id in plan.task_check_list_ids:
                            if eq_id.equipment_id.id == rec.id:
                                prev_mps += plan
                    if prev_mps:
                        prev_mps_lst.append(prev_mps.id)

            rec.odometer_mp_ids = [(4, x, None) for x in odometer_mps_lst]
            rec.odometer_mp_count = len(odometer_mps_lst)

            rec.hourmeter_mp_ids = [(4, x, None) for x in hourmeter_mps_lst]
            rec.hourmeter_mp_count = len(hourmeter_mps_lst)

            rec.preventive_mp_ids = [(4, x, None) for x in prev_mps_lst]
            rec.preventive_mp_count = len(prev_mps_lst)

    def action_view_odometer_mp(self):
        self.ensure_one()
        plan_data = self.env['maintenance.plan'].search([])
        main_main_plan_lst = self.env['maintenance.plan'].search([('is_odometer_m_plan', '=', True)]).mapped('id')
        check_main_plan_lst = self.env['plan.task.check.list'].search([('equipment_id', '=', self.id)]).mapped('maintenance_plan_id.id')
        equi_main_plan_lst = plan_data.filtered(lambda odo: self.category_id in odo.maintenance_category_ids).mapped('id')

        action_lst = []
        for eq in equi_main_plan_lst:
            if eq in main_main_plan_lst:
                action_lst.append(eq)
        for eq1 in check_main_plan_lst:
            if eq1 in main_main_plan_lst:
                action_lst.append(eq1)
        action_lst = list(set(action_lst))
        view_form_id = self.env.ref('maintenance_plan.maintenance_plan_view_form').id
        view_tree_id = self.env.ref('maintenance_plan.maintenance_plan_view_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', action_lst)],
            'view_mode': 'tree,form',
            'name': _('Odometer Maintenance Plan'),
            'res_model': 'maintenance.plan',
            'context': {'default_equipment_id': self.id, 'default_is_odometer_m_plan': True}
        }
        if len(self.odometer_mp_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.odometer_mp_ids.id})
        else:
            action['views'] = [(view_tree_id, 'tree'), (view_form_id, 'form')]
        return action

    def action_view_hourmeter_mp(self):
        self.ensure_one()
        plan_data = self.env['maintenance.plan'].search([])
        main_main_plan_lst = self.env['maintenance.plan'].search([('is_hourmeter_m_plan', '=', True)]).mapped('id')
        check_main_plan_lst = self.env['plan.task.check.list'].search([('equipment_id', '=', self.id)]).mapped('maintenance_plan_id.id')
        equi_main_plan_lst = plan_data.filtered(lambda odo: self.category_id in odo.maintenance_category_ids).mapped('id')
        action_lst = []
        for eq in equi_main_plan_lst:
            if eq in main_main_plan_lst:
                action_lst.append(eq)
        for eq1 in check_main_plan_lst:
            if eq1 in main_main_plan_lst:
                action_lst.append(eq1)
        action_lst = list(set(action_lst))
        view_form_id = self.env.ref('maintenance_plan.maintenance_plan_view_form').id
        view_tree_id = self.env.ref('maintenance_plan.maintenance_plan_view_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', action_lst)],
            'view_mode': 'tree,form',
            'name': _('Hourmeter Maintenance Plan'),
            'res_model': 'maintenance.plan',
            'context': {'default_equipment_id': self.id}
        }
        if len(self.hourmeter_mp_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.hourmeter_mp_ids.id})
        else:
            action['views'] = [(view_tree_id, 'tree'), (view_form_id, 'form')]
        return action

    def action_view_preventive_mp(self):
        self.ensure_one()
        plan_data = self.env['maintenance.plan'].search([])
        main_main_plan_lst = self.env['maintenance.plan'].search([('is_preventive_m_plan', '=', True)]).mapped('id')
        check_main_plan_lst = self.env['plan.task.check.list'].search([('equipment_id', '=', self.id)]).mapped('maintenance_plan_id.id')
        equi_main_plan_lst = plan_data.filtered(lambda odo: self.category_id in odo.maintenance_category_ids).mapped('id')
        action_lst = []
        for eq in equi_main_plan_lst:
            if eq in main_main_plan_lst:
                action_lst.append(eq)
        for eq1 in check_main_plan_lst:
            if eq1 in main_main_plan_lst:
                action_lst.append(eq1)
        action_lst = list(set(action_lst))
        view_form_id = self.env.ref('maintenance_plan.maintenance_plan_view_form').id
        view_tree_id = self.env.ref('maintenance_plan.maintenance_plan_view_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', action_lst)],
            'view_mode': 'tree,form',
            'name': _('Preventive Maintenance Plan'),
            'res_model': 'maintenance.plan',
            'context': {'default_equipment_id': self.id}
        }
        if len(self.preventive_mp_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.preventive_mp_ids.id})
        else:
            action['views'] = [(view_tree_id, 'tree'), (view_form_id, 'form')]
        return action

    hm_unit = fields.Selection([
        ('hour', 'hours'),
        ('jam', 'j')
        ], 'Hour meter Unit', default='hour', help='Unit of the hourmeter ', required=True)

    def _compute_hm_count(self):
        for rec in self:
            hm_count = self.env['maintenance.hour.meter'].search_count([('maintenance_asset', '=', rec.id)])
            rec.hm_count = hm_count

    def _compute_repair_count(self):
        repair_obj = self.env['maintenance.repair.order']
        repair_ids = repair_obj.search([('facilities_area','=', self.id)])
        for book in self:
            book.update({
                'repair_count' : len(repair_ids)
                })

    def _compute_request_count(self):
        for rec in self:
            request_count = self.env['maintenance.request'].search_count([('equipment_id', '=', rec.id)])
            rec.request_count = request_count

    def _compute_wo_count(self):
        for rec in self:
            wo_count = self.env['maintenance.work.order'].search_count([('facility', '=', rec.id)])
            rec.wo_count = wo_count

    def _compute_work_order_count(self):
        work_order_obj = self.env['maintenance.work.order']
        work_order_ids = work_order_obj.search([('facility','=', self.id)])
        for book in self:
            book.update({
                'wo_count' : len(work_order_ids)
                })
    def _compute_am_count(self):
        for rec in self:
            am_count = self.env['inter.asset.transfer'].search_count([('asset_ids.asset_id', '=', rec.id)])
            rec.am_count = am_count

    def wo_action_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Work Order',
            'res_model': 'maintenance.work.order',
            'domain': [('facility','=',self.id)]}

    def asset_moves_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Asset Moves',
            'res_model': 'inter.asset.transfer',
            'domain': [('asset_ids.asset_id','=',self.id)]}

    def repair_action_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Repair',
            'res_model': 'maintenance.repair.order',
            'domain': [('facilities_area','=',self.id)]}

    # def send_notification_to_user(self):
    #     equipment_obj = self.env['maintenance.equipment'].search([])
    #     for rec in equipment_obj:
    #         if rec.important_documents_line:
    #             for line in rec.important_documents_line:
    #                 expiry_date = line.expiry_date
    #                 week_before_expiry = expiry_date - timedelta(days=7)
    #                 if fields.Date.today() == week_before_expiry:
    #                     user_id = self.env['res.users'].search([('id', '=', line.create_uid.id)])
    #                     #sent chat box notification
    #                     notification_ids = []
    #                     notification_ids.append((0, 0, {'res_partner_id': user_id.partner_id.id, 'notification_type':'inbox'}))
    #                     self.env['mail.message'].create({
    #                         'message_type': 'notification',
    #                         'body': 'Your document %s is expiring in 7 days' % (line.name),
    #                         'subject': 'Document Expiry',
    #                         'partner_ids': [(6, 0, [user_id.partner_id.id])],
    #                         'model': self._name,
    #                         'res_id': rec.id,
    #                         'notification_ids': notification_ids,
    #                         'author_id': self.env.user.partner_id.id
    #                     })


    @api.depends('important_documents_line')
    def _compute_total_expired_documents(self):
        for rec in self:
            total_expired = 0
            rec.expired_type = False
            if rec.important_documents_line:
                for line in rec.important_documents_line:
                    if line.expiry_date < fields.Date.today() or line.expiry_date - timedelta(days=line.alert_notif) < fields.Date.today():
                        total_expired += 1

            expired_types = [x.expired_type for x in rec.important_documents_line if x]
            if 'expired' in expired_types and 'expired_soon' in expired_types:
                rec.expired_type = 'both'
                rec.color = 1
            elif 'expired' in expired_types:
                rec.expired_type = 'expired'
                rec.color = 1
            elif 'soon' in expired_types:
                rec.expired_type = 'soon'
                rec.color = 3
            rec.total_expired_document = total_expired
            
    @api.model
    def action_regenerate_qrcode(self):
        for record in self:
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            parsed_url = urlparse(base_url)
            base_url = f'{parsed_url.netloc}/page/asset_information/?asset={record.id}'

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
            record.qr_code = qr_image


class MaintenanceEquipmentCategory(models.Model):
    _inherit = 'maintenance.equipment.category'

    odometer_mp_count = fields.Integer(string="Odometer Plans", compute='_compute_plan_count')
    hourmeter_mp_count = fields.Integer(string="Hourmeter Plans", compute='_compute_plan_count')
    preventive_mp_count = fields.Integer(string="Preventive Plans", compute='_compute_plan_count')



    autogenerate_asset = fields.Boolean('Autogenerate Asset Code', default=False)
    category_prefix_preference = fields.Selection([('all', 'All Asset in this Category will have some Prefix'),
                               ('additional', 'Additional Prefix will be define On Asset')],
                            string='Prefix Preference', default='all')
    asset_prefix = fields.Char('Asset Category Prefix')
    digits = fields.Integer('Digits', default=3)
    current_sequence = fields.Char('Current Sequence', default='1', readonly=True)

    @api.constrains('asset_prefix')
    def _check_prefix_limit(self):
        for record in self:
            if record.autogenerate_asset:
                IrConfigParam = self.env['ir.config_parameter'].sudo()
                prefix_limit = int(IrConfigParam.get_param('prefix_limit', 5))
                if len(record.asset_prefix) > prefix_limit:
                    raise ValidationError("Prefix value size must be less or equal to %s" % (prefix_limit))

    @api.onchange('digits')
    def generate_current_sequence(self):
        number = self.current_sequence.lstrip('0')
        if self.digits < len(number):
            raise ValidationError(_('Digits Not Acceptable!'))
        if self.digits >= 8:
            raise ValidationError(_('Maximum digits is 7!'))
        current_sequence_length = len(self.current_sequence)
        if self.digits > current_sequence_length:
            number_length = len(number)
            original_number_length = self.digits - number_length
            add_zero_original_number = '0' * original_number_length
            self.current_sequence = add_zero_original_number + number
        elif self.digits < current_sequence_length:
            self.current_sequence = self.current_sequence[-self.digits:]

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            split_name = self.name.split(" ")
            if len(split_name) == 1:
                name = split_name[0][:3].upper()
                self.asset_prefix = name
            elif len(split_name) == 2:
                name = split_name[0][0]
                name_1 = split_name[1][0]
                name_2 = ''
                if len(split_name[1]) > 1:
                    name_2 = split_name[1][1]
                final_name = (name + name_1 + name_2).upper()
                self.asset_prefix = final_name
            elif len(split_name) > 2:
                name = split_name[0][0]
                name_1 = split_name[1][0]
                name_2 = split_name[2][0]
                final_name = (name + name_1 + name_2).upper()
                self.asset_prefix = final_name
        else:
            self.asset_prefix = False


    def _compute_plan_count(self):
        self.odometer_mp_count = None
        self.hourmeter_mp_count = None
        self.preventive_mp_count = None
        plan_date = self.env['maintenance.plan'].search([])
        for rec in self:
            rec.odometer_mp_count = len(plan_date.filtered(lambda odo: rec.id in odo.maintenance_category_ids.ids and odo.is_odometer_m_plan == True))
            rec.hourmeter_mp_count = len(plan_date.filtered(lambda odo: rec.id in odo.maintenance_category_ids.ids and odo.is_hourmeter_m_plan == True))
            rec.preventive_mp_count = len(plan_date.filtered(lambda odo: rec.id in odo.maintenance_category_ids.ids and odo.is_preventive_m_plan == True))

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Asset Categories'),
            'template': '/equip3_asset_fms_masterdata/static/xls/asset_categories_template.xls'
        }]

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    
    # category_id = fields.Many2one(required=False)
    equipment_id = fields.Many2one('maintenance.equipment', string="Reference", tracking=True)

# class AccountAssetSale(models.TransientModel):
#     _inherit = 'asset.asset.sale'

#     def confirm_asset_sale(self):
#         res = super(AccountAssetSale, self).confirm_asset_sale()
#         if self.state == 'open':
#             self.equipment_id.write({'state': 'sold'})
#             self.equipment_id.sale_at = fields.Date.today()
#         else:
#             raise UserError(_('You can only sell assets that are in running state.'))
#         return res

# class AccountAssetDepreciationLine():
#     _inherit='account.asset.depreciation.line'

#     def post_lines_and_close_asset(self):
#         res = super(AccountAssetDepreciationLine, self).post_lines_and_close_asset()
#         for line in self:
#             asset = line.asset_id
#             if asset.currency_id.is_zero(asset.value_residual):
#                 asset.equipment_id.scrapped_at = fields.Date.today()
#         return res

class ImortantDocumentLine(models.Model):
    _name = 'important.document.line'
    _description = 'Importan Document Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    equipment_id = fields.Many2one('maintenance.equipment', string="Reference")
    name = fields.Char(string="Document Name", required=True)
    expiry_date = fields.Date(string="Expiry Date", required=True)
    latest_renewal_date = fields.Date(string="Latest Renewal")
    # attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    attachment_file = fields.Binary(string="Attached File")
    file_name = fields.Char(string="Attached File Name")
    alert_notif = fields.Integer(string='Alert Notification (Days)', required=True)
    expired_type = fields.Selection([('soon', 'Expired Soon'), ('expired', 'Expired')], string="Expired Type", compute="_compute_expired_type")

    @api.depends('expiry_date')
    def _compute_expired_type(self):
        today = fields.Date.today()
        for record in self:
            record.expired_type = False
            if record.expiry_date and record.alert_notif:
                expiry_date = record.expiry_date
                if expiry_date < today:
                    record.expired_type = 'expired'
                elif expiry_date - timedelta(days=record.alert_notif) <= today:
                    record.expired_type = 'soon'


    @api.model
    def create(self, vals):
        res = super(ImortantDocumentLine, self).create(vals)
        if vals:
            message = 'Important Document Created with Name: ' + vals['name']
            res.equipment_id.message_post(body=message, subject="Important Document")
        return res

    def write(self, vals):
        name = self.name
        res = super(ImortantDocumentLine, self).write(vals)
        if vals:
            message = 'Document ' + name + ' Updated'
            self.equipment_id.message_post(body=message, subject="Important Document")
        return res

    # def unlink(self):
    #     name = self.name
    #     res = super(ImortantDocumentLine, self).unlink()
    #     message = 'Document ' + name + ' Deleted'
    #     self.equipment_id.message_post(body=message, subject="Important Document")
    #     return res
