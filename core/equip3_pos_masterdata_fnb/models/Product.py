# -*- coding: utf-8 -*

from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # is_employee_meal = fields.Boolean('Employee Meal')
    is_combo_product_new = fields.Boolean('Combo Product (New)')
    pos_combo_ids = fields.One2many('pos.combo','product_tmpl_id', string='Pos Combo')
    is_product_bom = fields.Boolean('Product BoM', compute='_compute_is_product_bom')
    pos_bom_id = fields.Many2one('mrp.bom', compute='_compute_pos_bom_id', string='Pos BoM')

    def pos_bom_domain(self):
        domain = ['|', ('product_id', 'in', self.product_variant_ids.ids), 
                  '&', ('product_id', '=', False),('product_tmpl_id', '=', self.id)]
        domain += [('is_pos_bom','=',True)]
        return domain

    def _compute_pos_bom_id(self):
        for product in self:
            domain = product.pos_bom_domain()
            product.pos_bom_id = self.env['mrp.bom'].search(domain, limit=1)

    def _compute_is_product_bom(self):
        for product in self:
            domain = product.pos_bom_domain()
            bom = self.env['mrp.bom'].search_read(domain, ['id'], limit=1)
            product.is_product_bom = bom and True or False


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    is_combo_product_new = fields.Boolean('Combo Product (New)', related='product_tmpl_id.is_combo_product_new')    
    pos_combo_ids = fields.One2many('pos.combo', string='Pos Combo', compute='_compute_pos_combo_ids')
    is_product_bom = fields.Boolean('Product BoM', compute='_compute_is_product_bom')
    pos_bom_id = fields.Many2one('mrp.bom', compute='_compute_pos_bom_id', string='Pos BoM')

    def _compute_pos_combo_ids(self):
        for rec in self:
            pos_combo_ids = False
            if rec.product_tmpl_id:
                if rec.product_tmpl_id.pos_combo_ids:
                    pos_combo_ids = rec.product_tmpl_id.pos_combo_ids
            rec.pos_combo_ids = pos_combo_ids

    def pos_bom_domain(self):
        domain = ['|', ('product_id', '=', self.id), 
                  '&', ('product_id', '=', False), ('product_tmpl_id', '=', self.product_tmpl_id.id)]
        domain += [('is_pos_bom','=',True)]
        return domain

    
    def _compute_is_product_bom(self):
        bom_by_product_tmpl = []
        bom_by_product = []

        query = '''
            SELECT mb.product_id, mb.id 
            FROM mrp_bom AS mb
            WHERE mb.is_pos_bom = 't'
                AND mb.product_id IN (%s)
            GROUP BY mb.product_id, mb.id
        ''' % (str(self.ids)[1:-1])
        self.env.cr.execute(query)        
        results = self.env.cr.fetchall()
        bom_by_product = [x[0] for x in results]

        product_tmpl_ids = [p.product_tmpl_id.id for p in self if p.product_tmpl_id]
        if product_tmpl_ids:
            query = '''
                SELECT mb.product_tmpl_id, mb.id 
                FROM mrp_bom AS mb
                WHERE mb.is_pos_bom = 't'
                    AND mb.product_tmpl_id IN (%s)
                GROUP BY mb.product_tmpl_id, mb.id
            ''' % (str(product_tmpl_ids)[1:-1])
            self.env.cr.execute(query)
            results = self.env.cr.fetchall()
            bom_by_product_tmpl = [x[0] for x in results]

        for product in self:
            is_product_bom = False
            if bom_by_product:
                if product.id in bom_by_product:
                    is_product_bom = True

            if bom_by_product_tmpl:
                if product.product_tmpl_id.id in bom_by_product_tmpl:
                    is_product_bom = True

            product.is_product_bom = is_product_bom

    def _compute_pos_bom_id(self):
        for product in self:
            domain = product.pos_bom_domain()
            product.pos_bom_id = self.env['mrp.bom'].search(domain, limit=1)