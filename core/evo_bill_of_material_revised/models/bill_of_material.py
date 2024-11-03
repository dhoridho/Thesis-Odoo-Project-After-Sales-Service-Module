from odoo import api, fields, models,_
from odoo.exceptions import UserError


class BillOfMaterial(models.Model):
    _inherit = 'mrp.bom'
    _description = "Bill Of Material"

    revision_name = fields.Float('Version',copy=True,readonly=True,default=0.001)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('revised', 'Revised'),
        ('confirm', 'Active'),
        ], string='State', readonly=True, copy=False, index=True, tracking=3, default='draft')
    current_revision_id = fields.Many2one('mrp.bom','Current Revision',readonly=True,copy=True)
    old_revision_ids = fields.One2many('mrp.bom','current_revision_id','Old Revision',readonly=True,context={'active_test': False})
    revision_no = fields.Integer('Revised',copy=False)
    
    @api.model
    def _bom_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False,state='confirm'):
        """ Finds BoM for particular product, picking and company """
        if product and product.type == 'service' or product_tmpl and product_tmpl.type == 'service':
            return self.env['mrp.bom']
        domain = self._bom_find_domain(product_tmpl=product_tmpl, product=product, picking_type=picking_type, company_id=company_id, bom_type=bom_type,state='confirm')
        if domain is False:
            return self.env['mrp.bom']
        domain += [('state', '=', 'confirm')]
        return self.search(domain, order='sequence, product_id', limit=1)
    
    @api.model
    def _bom_find_domain(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False,state='confirm'):
        if product:
            if not product_tmpl:
                product_tmpl = product.product_tmpl_id
            domain = ['|', ('product_id', '=', product.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl.id)]
        elif product_tmpl:
            domain = [('product_tmpl_id', '=', product_tmpl.id)]
        else:
            raise UserError(_('You should provide either a product or a product template to search a BoM'))
        if picking_type:
            domain += ['|', ('picking_type_id', '=', picking_type.id), ('picking_type_id', '=', False)]
        if company_id or self.env.context.get('company_id'):
            domain = domain + ['|', ('company_id', '=', False), ('company_id', '=', company_id or self.env.context.get('company_id'))]
        if bom_type:
            domain += [('type', '=', bom_type)]
        domain += [('state', '=', 'confirm')]
        return domain

    @api.model
    def create(self, vals):
        if 'revision_name' not in vals:
            vals['revision_name'] = 1.001
        return super(BillOfMaterial, self).create(vals)

   
    def create_revised(self):
        if self.env.context.get('for_new_revised'):
            self.ensure_one()
            view_ref = self.env['ir.model.data'].get_object_reference('mrp', 'mrp_bom_form_view')
            view_id = view_ref and view_ref[1] or False,
            self.with_context(new_bom_revised=True,for_new_revised=True).copy()
        if self.env.context.get('for_restore_revised'):
            self.ensure_one()
            view_ref = self.env['ir.model.data'].get_object_reference('mrp', 'mrp_bom_form_view')
            view_id = view_ref and view_ref[1] or False,
            self.with_context(new_bom_revised=True,for_restore_revised=True).copy()   
        return {
            'type': 'ir.actions.act_window',
            'name': ('Bill of Material'),
            'res_model': 'mrp.bom',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    @api.returns('self', lambda value: value.id)
    def copy(self, defaults=None):
        if not defaults:
            defaults = {}
        if self.env.context.get('new_bom_revised'):
            if not self.revision_name:
                self.revision_name = 1.001
            if self.env.context.get('for_new_revised'):
                prev_name = self.revision_name
            if self.env.context.get('for_restore_revised'):
                prev_name = self.current_revision_id.revision_name
            if not self.revision_no:
                self.revision_no = 1
            revno = self.revision_no
            if self.env.context.get('revised_for_minor'):
                new_revision_name = prev_name + 0.001
            if self.env.context.get('revised_for_major'):
                new_revision_name = int(prev_name) + 1.000
                
            self.write({'revision_no': str(revno + 1) ,'revision_name':new_revision_name,'state':'draft'})
            defaults.update({'revision_no': revno,'current_revision_id': self.id,'revision_name': prev_name,'state': 'revised'})
        return super(BillOfMaterial, self).copy(defaults)

    def action_go_revised(self):
        if not self.revision_name:
            self.revision_name = 1.001
        prev_name = self.current_revision_id.revision_name
        new_revision_name = prev_name + 0.001
        form_view_id = self.env.ref('evo_bill_of_material_revised.view_revised_bom_wizard')
        return {
            'name': _('Revision Bill Of Material'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'revised.bom.wizard',
            'views': [(form_view_id.id, 'form')],
            'view_id': form_view_id.id,
            'target': 'new',
            'context':{'default_bom_id': self.id,'default_minor_next_version': new_revision_name,'for_new_revised':True},
        }
        
    def action_active_revised(self):
        self.write({'state': 'confirm'})
        
    def action_restore_revised(self):
        prev_name = self.current_revision_id.revision_name
        new_revision_name = prev_name + 0.001
        form_view_id = self.env.ref('evo_bill_of_material_revised.view_revised_bom_wizard')
        return {
            'name': _('Revision Bill Of Material'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'revised.bom.wizard',
            'views': [(form_view_id.id, 'form')],
            'view_id': form_view_id.id,
            'target': 'new',
            'context':{'default_bom_id': self.id,'default_minor_next_version': new_revision_name,'for_restore_revised':True},
        }

BillOfMaterial()





