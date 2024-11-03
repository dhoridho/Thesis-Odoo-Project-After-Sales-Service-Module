from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = "pos.order"


    is_ph_training_mode = fields.Boolean('PH Training Mode')


    @api.model
    def create(self,vals):

        res = super(PosOrder,self).create(vals)
        if res.config_id.is_ph_training_mode:
            name = res.name
            if name == '/':
                name =  res.config_id.sequence_id._next()
            name = 'Training '+ name
            res.write({'is_ph_training_mode':True,'name':name})

        return res


    def _create_order_picking(self):
        if self.is_ph_training_mode:
            return False
        return super(PosOrder,self)._create_order_picking()