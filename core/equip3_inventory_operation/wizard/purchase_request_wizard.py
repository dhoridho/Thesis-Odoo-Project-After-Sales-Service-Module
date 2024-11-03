from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, ValidationError

class PurchaseRequestWizard(models.TransientModel):
    _name = 'purchase.request.wizard'
    _description = 'Purchase Request Wizard'

    pr_wizard_line = fields.One2many('purchase.request.wizard.line', 'mr_pr_wizard')

    def prepare_line(self, line):
        return {
            'mr_line_id': line.mr_line_id.id,
            'product_id' : line.product_id.id,
            'name' : line.description,
            'product_uom_id' : line.uom_id.id,
            'product_qty' : line.qty_purchase,
            'is_goods_orders': True,
            'date_required' : line.request_date,
            'company_id' : line.mr_id.company_id.id,
            'dest_loc_id': line.mr_id.destination_warehouse_id.id,
        }
    
    def prepare_pr(self):
        warehouse_id = False
        warehouse_id = self.pr_wizard_line[-1].mr_id.destination_warehouse_id if self.pr_wizard_line else False
        return {
            'line_ids': [(0, None, self.prepare_line(line)) for line in self.pr_wizard_line ],
            'is_goods_orders': True, 
            'origin': self.pr_wizard_line and self.pr_wizard_line[-1].mr_id.name or '',
            'picking_type_id': warehouse_id and warehouse_id.in_type_id.id,
            'branch_id': self.pr_wizard_line[-1].mr_line_id.material_request_id.branch_id.id if self.pr_wizard_line else False,
            'mr_id': self.pr_wizard_line.mr_id
        }

    def create_pr(self):
        mr_id = self.pr_wizard_line[0].mr_id
        mr_id._check_processed_record(mr_id.id)
        vals = self.prepare_pr()
        return self.env['purchase.request'].create(vals)




class PurchaseRequestWizardLine(models.TransientModel):
    _name = 'purchase.request.wizard.line'
    _description = 'Purchase Request Wizard Line'

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequestWizardLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'pr_wizard_line' in context_keys:
                if len(self._context.get('pr_wizard_line')) > 0:
                    next_sequence = len(self._context.get('pr_wizard_line')) + 1
            res.update({'no': next_sequence})
        return res

    mr_id = fields.Many2one('material.request', 'Material Request')
    no = fields.Integer('No', readonly='1')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Char()
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    qty_purchase = fields.Float('Quantity to Purchase', required='1')
    request_date = fields.Date('Request Date', required='1')
    mr_pr_wizard = fields.Many2one('purchase.request.wizard')
    mr_line_id = fields.Many2one('material.request.line')
    dest_warehouse_id = fields.Many2one(related='mr_id.destination_warehouse_id')




class ShowMaterialDonePopup(models.TransientModel):
    _name = 'show.material.done.popup'
    _description = 'Show Material Done Popup'

    def force_done_material_request(self):
        material_request_id = self.env['material.request'].browse(self._context.get('active_ids'))
        for line in material_request_id.product_line:
            line.write({'quantity': line.done_qty})
        material_request_id.write({'status': 'done'})


class PRWizard(models.TransientModel):
    _name = 'mr_line.pr.wizard'
    _description = 'MR Line PR Wizard'

    def _default_pr_wizard_line(self):
        mr_lines_id = self.env['material.request.line'].browse(self._context.get('active_ids'))
        pr_line = []
        count = 1
        error_lines = []
        counter = 1
        for rec in mr_lines_id:
            if rec.status != 'confirm':
                if rec.status == 'draft':
                    error_lines.append("- Product %s in Material Request %s  must be confirmed to create Purchase Request" % (rec.product.name, rec.material_request_id.name))
                if rec.status == 'done':
                    error_lines.append("- Product %s in Material Request %s  request was done" % (rec.product.name, rec.material_request_id.name))
            qty = rec.quantity - rec.done_qty
            if qty < 0:
                qty = 0
            vals = {
                'no': count,
                'mr_id': rec.material_request_id.id,
                'product_id' : rec.product.id,
                'description' : rec.product.description,
                'uom_id' : rec.product.uom_id.id,
                'qty_purchase' : qty,
                'request_date' : rec.request_date,
                'mr_line_id': rec.id,
            }
            pr_line.append((0,0, vals))
            count = count+1
        if error_lines:
            raise ValidationError("%s" % ('\n'.join(error_lines)))

        return pr_line


    pr_wizard_line = fields.One2many('mr_line.pr.wizard_line', 'mr_pr_wizard', default=_default_pr_wizard_line)


    def create_pr(self):
        dest_loc = []
        qty_in_progress = 0
        done_qty = 0
        req_quantity = 0
        pr_id_list = []
        for line in self.pr_wizard_line:
            qty_in_progress += line.mr_line_id.progress_quantity
            done_qty += line.mr_line_id.done_qty
            req_quantity += line.mr_line_id.requested_qty
            if line.mr_id.destination_warehouse_id not in dest_loc:
                dest_loc.append(line.mr_id.destination_warehouse_id)
            quantity = line.qty_purchase + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
            if quantity > line.mr_line_id.quantity:
                raise ValidationError(_('You cannot create a PR for %s with more quantity then you Requested.') %
                (line.product_id.name))
        for mr in dest_loc:
            pr_line = []
            mr_list = []
            origin = []
            warehouse_id = False
            for line in self.pr_wizard_line:
                if mr.id == line.mr_id.destination_warehouse_id.id:
                    vals = {
                        'product_id' : line.product_id.id,
                        'name' : line.description,
                        'product_uom_id' : line.uom_id.id,
                        'product_qty' : line.qty_purchase,
                        'is_goods_orders': True,
                        'date_required' : line.request_date,
                        'mr_line_id':line.mr_line_id.id,
                        'company_id' : line.mr_id.company_id.id,
                        'dest_loc_id': line.mr_id.destination_warehouse_id.id,
                    }
                    warehouse_id = line.mr_id.destination_warehouse_id
                    pr_line.append((0,0, vals))
                    mr_list.append(line.mr_id.id)
                    if line.mr_id.name not in origin:
                        origin.append(line.mr_id.name)
            pr_id = self.env['purchase.request'].create({'line_ids': pr_line, 'origin': ','.join(origin),
                                                         'is_goods_orders': True, 'picking_type_id': mr.in_type_id.id})
            pr_id.write({
                'mr_id': [(6, False, mr_list)]
            })
            for pr in pr_id.line_ids:
                mr_lines_id = self.env['material.request.line'].search([('id','=',pr.mr_line_id.id),('product','=',pr.product_id.id)])
                for rec in mr_lines_id:
                    rec.write({'pr_lines_ids': [(4, pr.id)]})
            pr_id_list.append(pr_id)
        return




class PRWizardLine(models.TransientModel):
    _name = 'mr_line.pr.wizard_line'
    _description = 'MR Line PR Wizard Line'

    @api.model
    def default_get(self, fields):
        res = super(PRWizardLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'pr_wizard_line' in context_keys:
                if len(self._context.get('pr_wizard_line')) > 0:
                    next_sequence = len(self._context.get('pr_wizard_line')) + 1
            res.update({'no': next_sequence})
        return res

    mr_id = fields.Many2one('material.request', 'Reference')
    mr_line_id = fields.Many2one('material.request.line')
    no = fields.Integer('No', readonly='1')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Char()
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    qty_purchase = fields.Float('Quantity to Purchase', required='1')
    request_date = fields.Date('Request Date', required='1')
    dest_warehouse_id = fields.Many2one(related='mr_id.destination_warehouse_id')
    mr_pr_wizard = fields.Many2one('mr_line.pr.wizard')

