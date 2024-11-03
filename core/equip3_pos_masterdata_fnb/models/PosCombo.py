# -*- coding: utf-8 -*

from odoo import api, fields, models, _

class PosCombo(models.Model):
    _name = 'pos.combo'
    _description = 'Pos Combo'

    name = fields.Char('Name')
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    maximum_pick = fields.Integer('Maximum Pick', default=1)
    required = fields.Boolean('Required')
    option_ids = fields.One2many('pos.combo.option','pos_combo_id', string='Options')
    show_details_visible = fields.Integer(compute='_compute_show_details_visible', string='Show Detail Visible')

    def action_show_details(self):
        return {
            'name': _('Options'),
            'res_model': 'pos.combo',
            'view_mode': 'form',
            'views': [(self.env.ref('equip3_pos_masterdata_fnb.pos_combo_form_view').id,'form')],
            'context': {'default_pos_combo_id': self.id,},
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new',
        }
    def _compute_show_details_visible(self):
        for rec in self:
            is_visible = True
            if not rec.create_date:
                is_visible = False
            if not rec.option_ids:
                is_visible = False
            rec.show_details_visible = is_visible

    @api.onchange('maximum_pick')
    def _onchange_maximum_pick(self):
        if self.maximum_pick == 0:
            self.maximum_pick = 1

class PosComboOption(models.Model):
    _name = 'pos.combo.option'
    _description = 'Pos Combo Option'
    _rec_name = 'product_id'

    pos_combo_id = fields.Many2one('pos.combo', string='Category')
    product_id = fields.Many2one('product.product', string='Product')
    extra_price = fields.Float(string='Extra Price')
    pos_bom_line_ids = fields.Many2many('mrp.bom.line', string='POS Bom Components', compute='_compute_pos_bom_line_ids')
    is_configure_components = fields.Boolean('Configure Components', compute='_compute_is_configure_components')
    store_uom_id = fields.Many2one('uom.uom','Store UOM',copy=False)
    uom_id = fields.Many2one('uom.uom','UOM',store=False,compute='_compute_uom_id')

    def _compute_uom_id(self):
        for data in self:
            uom_id = data.product_id.uom_id.id or False
            if data.store_uom_id:
                uom_id = data.store_uom_id.id
            data.uom_id = uom_id

    def _compute_pos_bom_line_ids(self):
        for rec in self:
            domain = [('id','=',-1)]
            product = rec.product_id
            if product.is_product_bom and product.pos_bom_id:
                domain = [('id','in',product.pos_bom_id.bom_line_ids.ids)]
            rec.pos_bom_line_ids = self.env['mrp.bom.line'].search(domain)

    def _compute_is_configure_components(self):
        for rec in self:
            is_configure_components = False
            if rec.product_id and rec.product_id.pos_bom_id:
                is_configure_components = rec.product_id.pos_bom_id.is_configure_components
            rec.is_configure_components = is_configure_components