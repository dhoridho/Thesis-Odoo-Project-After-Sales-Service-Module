from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime
from odoo import tools
import pytz

class AssetStockTake(models.Model):
    _name = 'asset.stock.take'
    _description = 'Asset Stock Take'

    name = fields.Char(string="Reference Inventory")
    fac_area = fields.Many2one('maintenance.facilities.area', string="Facilities Area")
    inventory_of = fields.Selection([('all asset','All Asset'), ('one asset category','One Asset Category'), ('select asset manually','Select Asset Manually')], default="select asset manually")
    acc_date = fields.Date('Accounting Date')
    branch = fields.Many2one('res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    asset_inventory_line = fields.One2many('asset.inventory.line', 'asset_stock_take_id', string='Asset')
    asset_category = fields.Many2one('maintenance.equipment.category', string="Asset Category")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('in_progress', 'In Progress'),
         ('validate', 'Validate'),
         ('cancel', 'Cancelled')], string="State", default='draft', group_expand='_expand_states')
    scanned_value = fields.Char('Scanned Barcode')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.onchange('scanned_value')
    def get_scanned_barcode(self):
        for rec in self:
            if rec.scanned_value:
                equip_id = int(str(rec.scanned_value).split("asset=")[1])
                equip_obj = self.env['maintenance.equipment'].browse(equip_id)
                if rec.fac_area == equip_obj.fac_area:
                    vals = ({'asset_id':equip_obj.id,
                            'serial_no': equip_obj.serial_no,
                            'fac_area': equip_obj.fac_area,
                            'state_equip': equip_obj.state})
                    rec.asset_inventory_line = [(0, 0, vals)]
                    rec.scanned_value = ""
                else:
                    raise ValidationError(_('Asset not found in the selected Facilities Area'))


    @api.model
    def default_get(self, fields_list):
        defaults = super(AssetStockTake, self).default_get(fields_list)
        maintenance_record = self.env['maintenance.equipment'].search([])
        asset_line = []
        for record in maintenance_record:
            asset_line.append((0, 0, {
                'asset_id': record.id
            }))
        defaults.update({'asset_inventory_line' : asset_line})
        return defaults

    @api.onchange('fac_area', 'inventory_of', 'asset_category')
    def asset_filter_onchange(self):
        maintenance_record = False
        if self.fac_area:
            if self.inventory_of == 'all asset':
                maintenance_record = self.env['maintenance.equipment'].search([('fac_area', '=', self.fac_area.id), ('state', 'not in', ['sold','scrapped'])])
                if not maintenance_record:
                    self.asset_inventory_line = [(5, 0, 0)]
                    return {'warning': {'title': _('Warning'), 'message': _('No Asset found in this Facilities Area')}}
            elif self.inventory_of == 'one asset category':
                if self.asset_category:
                    maintenance_record = self.env['maintenance.equipment'].search([('fac_area', '=', self.fac_area.id), ('category_id', '=', self.asset_category.id), ('state', 'not in', ['sold','scrapped'])])
                    if not maintenance_record:
                        self.asset_inventory_line = [(5, 0, 0)]
                        return {'warning': {'title': _('Warning'), 'message': _('No Asset found in this Asset Category...!')}}
            else:
                maintenance_record = False
        else:
            if self.inventory_of == 'all asset':
                maintenance_record = self.env['maintenance.equipment'].search([('state', 'not in', ['sold','scrapped'])])

                if not maintenance_record:
                    self.asset_inventory_line = [(5, 0, 0)]
                    return {'warning': {'title': _('Warning'), 'message': _('Please add Asset or Vehicle before Inventory')}}
            elif self.inventory_of == 'one asset category':
                if self.asset_category:
                    maintenance_record = self.env['maintenance.equipment'].search([('category_id', '=', self.asset_category.id),('state', 'not in', ['sold','scrapped'])])
                    if not maintenance_record:
                        self.asset_inventory_line = [(5, 0, 0)]
                        return {'warning': {'title': _('Warning'), 'message': _('No Asset found in this Asset Category...!')}}
            else:
                maintenance_record = False
                self.asset_inventory_line = [(5,0,0)]
        if maintenance_record:
            self.asset_inventory_line = [(5, 0, 0)]
            task_check_list = []
            for record in maintenance_record:
                task_check_list.append((0, 0, {
                    'asset_id': record.id,
                    'real_state': record.state
                }))
            self.asset_inventory_line = task_check_list
        else:
            self.asset_inventory_line = [(5, 0, 0)]


    def state_start(self):
        self.write({'state': 'in_progress'})

    def action_validate(self):
        if self.asset_inventory_line:
            for record in self.asset_inventory_line:
                asset = self.env['maintenance.equipment'].search([('id', '=', record.asset_id.id)])
                if record.real_state:
                    if record.real_state not in ['missing', 'found']:
                        if record.real_state != record.state_equip:
                            asset.write({'state': record.real_state})
                        else:
                            asset.write({'state': record.real_state})
                    else:
                        if record.real_state == 'missing':
                            asset.write({'missing' : 'yes', 'missing_date': self.get_today(), 'state': record.real_state})
                        elif record.real_state == 'found':
                            asset.write({'missing' :'no', 'missing_date': False, 'state': 'operative'})
                else:
                    raise Warning(_('Please select status for asset %s') % (asset.name))
                if record.new_fac_area:
                    asset.write({'fac_area': record.new_fac_area})
            self.write({'state': 'validate'})
        else:
            raise Warning(_('Please Select Asset Before Validate...!'))

    def state_cancel(self):
        self.write({'state': 'cancel'})

    def state_draft(self):
        self.write({'state': 'draft'})

    def _expand_states(self, states, domain, order):
        return ['draft', 'in_progress', 'validate', 'cancel']

    def get_today(self):
        tz = pytz.timezone('Asia/Singapore')
        today = datetime.now(tz).date()
        return today

    @api.model
    def default_sh_asset_stock_bm_is_cont_scan(self):
        return self.env.company.sh_asset_stock_bm_is_cont_scan

    sh_asset_stock_barcode_mobile = fields.Char(string="Mobile Barcode")
    sh_asset_stock_bm_is_cont_scan = fields.Char(string='Continuously Scan?', default=default_sh_asset_stock_bm_is_cont_scan, readonly=True)

    @api.onchange('sh_asset_stock_barcode_mobile')
    def _onchange_sh_asset_stock_barcode_mobile(self):

        if self.sh_asset_stock_barcode_mobile in ['', "", False, None]:
            return

        if not self.scanned_value:
            self.scanned_value = self.sh_asset_stock_barcode_mobile

        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_asset_stock_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.user.company_id.sudo().sh_asset_stock_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        # step 1 make sure order in proper state.
        if self and self.state in ["cancel", "validate"]:
            selections = self.fields_get()["state"]["selection"]
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)

            if self.env.user.company_id.sudo().sh_asset_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You can not scan item in %s state.') % (value)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return

        # step 2 increaset product qty by 1 if product not in order line than create new order line.
        elif self:
            search_lines = False
            domain = []
            if self.env.user.company_id.sudo().sh_asset_stock_barcode_mobile_type == "barcode":
                search_lines = self.asset_inventory_line.filtered(
                    lambda ol: ol.asset_id.barcode == self.sh_asset_stock_barcode_mobile)

            if search_lines:
                for line in search_lines:
                    line.update({'real_state': 'found'})
                    self.sh_asset_stock_barcode_mobile = ''
                    if self.env.user.company_id.sudo().sh_asset_stock_bm_is_notify_on_success:
                        message = _(
                            CODE_SOUND_SUCCESS + 'Asset %s found') % (line.asset_id.name)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                            self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                    break

            else:
                if self.env.user.company_id.sudo().sh_asset_stock_bm_is_notify_on_fail:
                    message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any Asset Line!')
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True}
                    )


AssetStockTake()

class AssetInvenoryLine(models.Model):
    _name = 'asset.inventory.line'
    _description = 'Asset Inventory Line'
    
    def _default_real_state(self):
        for rec in self:
            if rec.state_equip in ('sold','scrapped'):
                rec.real_state = False
            else:
                rec.real_state = rec.state_equip
                

    asset_stock_take_id = fields.Many2one('asset.stock.take')
    state = fields.Selection(related='asset_stock_take_id.state', string="State")
    asset_id = fields.Many2one('maintenance.equipment', string="Asset", required=True)
    serial_no = fields.Char(related='asset_id.serial_no')
    fac_area = fields.Many2one('maintenance.facilities.area', string="Current Facilities Area", default=lambda self: self.asset_id.fac_area)
    new_fac_area = fields.Many2one('maintenance.facilities.area', string="New Facilities Area", default=lambda self: self.asset_id.fac_area)
    state_equip = fields.Selection([('operative','Operative'),('missing','Missing'), ('breakdown','Breakdown'),('maintenance','Maintenance'), ('scrapped','Scrapped'), ('sold', 'Sold')], string="Current Status", default=lambda self: self.asset_id.state)
    real_state = fields.Selection([('operative','Operative'),('missing','Missing'), ('breakdown','Breakdown'),('maintenance','Maintenance')], string="New Status", required=False, default=lambda self: self._default_real_state())
    is_missing = fields.Selection([('yes','Yes'), ('no','No')], string="Is Missing", default=lambda self: self._get_is_missing())
    attachment_ids = fields.Many2many('ir.attachment','asset_line_id', 'attachment_id', string='Attachment')
    
                
    @api.onchange('asset_id')
    def asset_onchange(self):
        self.state_equip = self.asset_id.state
        self.is_missing = self._get_is_missing()
        if self.asset_stock_take_id.inventory_of == 'select asset manually':
            self.fac_area = self.asset_id.fac_area
            self.new_fac_area = self.asset_id.fac_area
            self.state_equip =  self.asset_id.state
            self.real_state = self.asset_id.state
            if self.asset_stock_take_id.fac_area and self.is_missing:
                domain = [('fac_area', '=', self.asset_stock_take_id.fac_area.id), ('state', 'not in', ['sold', 'scrapped'])]
                return {'domain': {'asset_id': domain}}
        
    @api.model
    def _get_is_missing(self):
        if self.asset_id.state == 'missing':
            return 'yes'
        else:
            return 'no'
        
