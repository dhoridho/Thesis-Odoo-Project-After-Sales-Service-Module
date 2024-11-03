# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class WizMPProductUpdate(models.TransientModel):
    _name = 'wiz.mp.product.update'
    _description = 'Marketplace Product Update Wizard'

    mode = fields.Selection([
        ('stock_only', 'Stock Only'),
        ('price_only', 'Price Only'),
        ('activation', 'Activation'),
        ('detail', 'Detail'),
    ], default='stock_only', string='Mode')
    mp_account_ids = fields.Many2many('mp.account', string='Marketplace')
    line_ids = fields.One2many(comodel_name='wiz.mp.product.update.line', inverse_name='mode_id', string='Quick Line')
    activation_ids = fields.One2many(comodel_name='wiz.mp.product.activation.line', inverse_name='mode_id', string='Activation Line')
    
    mp_product_ids = fields.Many2many('mp.product', string='Products')
    mp_product_id = fields.Many2one('mp.product', string='Product', compute='get_mp_product_id')
    name = fields.Char()
    description = fields.Char()
    sku = fields.Char('SKU')
    condition = fields.Selection([('NEW', 'New'), ('USED', 'Used')], default='NEW')
    weight = fields.Float('Weight (Kg)')
    height = fields.Float('Height (Cm)')
    width = fields.Float('Width (Cm)')
    length = fields.Float('Length (Cm)')
    wholesale_ids = fields.One2many('wiz.mp.product.wholesale.line', 'mode_id')
    image_ids = fields.One2many('wiz.mp.product.image.line', 'mode_id')
    
    @api.onchange('mp_account_ids')
    def change_mp_account_ids(self):
        self.ensure_one()
        res = self.mp_product_ids.get_product().set_mp_data(skip_error=True, mp_account_ids=self.mp_account_ids)
        if not res:
            res = self.mp_product_ids.mp_product_variant_ids.get_product().set_mp_data(mp_account_ids=self.mp_account_ids)
        return res
    
    def get_mp_product_id(self):
        mp_product_id = self._context.get('mp_product_id')
        for rec in self:
            rec.mp_product_id = mp_product_id or None

    def update(self):
        for rec in self.filtered(lambda r:r.mode in ['stock_only', 'price_only']):
            mp_account_idset = list(set([mp_product_id.mp_account_id.id for mp_product_id in rec.line_ids.mapped('mp_product_id')]))
            mp_account_ids = self.env['mp.account'].browse(mp_account_idset)
            for mp_account_id in mp_account_ids:
                if mp_account_id in rec.mp_account_ids:
                    data = []
                    for line_id in rec.line_ids:
                        if line_id.mp_product_id.mp_account_id.id == mp_account_id.id:
                            data.append({
                                'product_obj': line_id.mp_product_id,
                                'stock': line_id.stock,
                                'price': line_id.price,
                            })
                    mp_account_id.action_set_product(data=data, mode=rec.mode)
        for rec in self.filtered(lambda r:r.mode == 'activation'):
            mp_account_ids = rec.activation_ids.mapped('mp_product_id').mapped('mp_account_id')
            for mp_account_id in mp_account_ids:
                if mp_account_id in rec.mp_account_ids:
                    data = []
                    for activation_id in rec.activation_ids:
                        if activation_id.mp_product_id.mp_account_id.id == mp_account_id.id:
                            data.append({
                                'product_obj': activation_id.mp_product_id,
                                'activate': activation_id.activate,
                            })
                    mp_account_id.action_set_product(data=data, mode=rec.mode)
        for rec in self.filtered(lambda r:r.mode == 'detail'):
            for mp_account_id in rec.mp_account_ids:
                for mp_product_id in rec.mp_product_ids.filtered(lambda r:r.mp_account_id == mp_account_id):
                    mp_account_id.action_set_product(data=rec.with_context(mp_product_id=mp_product_id), mode=rec.mode)


class WizMPProductUpdateLine(models.TransientModel):
    _name = 'wiz.mp.product.update.line'
    _description = 'Marketplace Product Update Wizard Line'

    mode = fields.Selection(related='mode_id.mode', string='Mode')
    mode_id = fields.Many2one(comodel_name='wiz.mp.product.update', string='Mode ID')
    mp_product_id = fields.Reference([
        ('mp.product', 'Product'),
        ('mp.product.variant', 'Product Variant'),
    ], string='Product', required=True)
    mp_account_id = fields.Many2one('mp.account', string='Marketplace', compute='get_mp_account_id')
    stock = fields.Integer(default=0)
    price = fields.Float(default=0.0)
    
    def get_mp_account_id(self):
        for rec in self:
            rec.mp_account_id = rec.mp_product_id.mp_account_id

    
class WizMPProductActivationLine(models.TransientModel):
    _name = 'wiz.mp.product.activation.line'
    _description = 'Marketplace Product Activation Wizard Line'

    mode = fields.Selection(related='mode_id.mode', string='Mode')
    mode_id = fields.Many2one(comodel_name='wiz.mp.product.update', string='Mode ID')
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='Product')
    mp_account_id = fields.Many2one('mp.account', string='Marketplace', compute='get_mp_account_id')
    activate = fields.Boolean(default=True)
    
    def get_mp_account_id(self):
        for rec in self:
            rec.mp_account_id = rec.mp_product_id.mp_account_id

    
class WizMPProductWholesaleLine(models.TransientModel):
    _name = 'wiz.mp.product.wholesale.line'
    _description = 'Marketplace Product Wholesale Wizard Line'
    _order = 'min_qty'

    mode_id = fields.Many2one(comodel_name='wiz.mp.product.update', string='Mode ID')
    min_qty = fields.Integer(default=0)
    price = fields.Float(default=0.0)

    
class WizMPProductImageLine(models.TransientModel):
    _name = 'wiz.mp.product.image.line'
    _description = 'Marketplace Product Image Wizard Line'
    _order = 'sequence'

    mode_id = fields.Many2one(comodel_name='wiz.mp.product.update', string='Mode ID')
    sequence = fields.Integer(default=1)
    image = fields.Binary(string="Image", attachment=False)
