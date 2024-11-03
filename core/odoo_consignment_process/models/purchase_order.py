# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    @api.model
    def get_agreement_term_deatils(self):
        agreement_terms = '''
            Consignment Agreement Template
            <br/><br/>
            This Consignment Agreement (the “Agreement”) states the terms and conditions that govern the contractual agreement between [CONSIGNOR], located at [ADDRESS] (the “Consignor”) and [CONSIGNEE], located at [ADDRESS] (the “Consignee”) who agree to be bound by this Agreement.
            WHEREAS, the Consignor owns right and title to the items described on Exhibit A attached hereto (the “Consigned Items”), and the Consignee desires to take possession of the Consigned Items with the intention of selling it to a third party.
            <br/><br/>
            NOW, THEREFORE, in consideration of the mutual covenants and promises made by the parties hereto, the Consignor and the Consignee (individually, each a “Party” and collectively, the “Parties”) covenant and agree as follows:
            RIGHT TO SELL. The Consignor hereby grants to the Consignee the exclusive right to display and sell the Consigned Items according to the terms and conditions of this Agreement.
            MINIMUM PRICE. The minimum price at which the Consignee may sell the Consigned Items shall be [AMOUNT] (the “Minimum Price”). In the event the Consignee sells the Consigned Items for less than the Minimum Price, the Consignor shall be entitled to the same payment the Consignor would receive as its share of the sale price under this Agreement had the Consigned Items been sold for the Minimum Amount.
            <br/><br/>
            CONSIGNMENT FEE. The Consignee shall be entitled to [PERCENTAGE] of the full purchase price of the Consigned Items (the “Consignment Fee”).
            Within [NUMBER] of days from the sale of the Consigned Items, the Consignee shall deliver to the Consignor the sale price of the Consigned Items less the Consignment Fee.
            INSURANCE. The Consignee represents and warrants that the Consignee shall maintain insurance coverage sufficient to compensate the Consignor for the fair market value of the Consigned Items in the event of damage due to fire, theft, or otherwise.
            <br/><br/>
            LOCATION OF ITEMS. The Consignee agrees and acknowledges that the Consigned Items shall only be kept and stored at [ADDRESS] unless otherwise agreed upon by the Consignor in writing.
            PandaTip: This is more peace of mind for the Consignor, who can be assured its items won’t be moved around from location to location.
            TIMEFRAME. In the event that all the Consigned Items are not sold by [DATE] all unsold Consigned Items shall be returned to the Consignor with all delivery costs borne by the Consignee.
            CONSIGNOR REPRESENTATION. The Consignor hereby represents and warrants that the Consignor holds full title (or has received, in writing, the authorization to sell the Consigned Items by any necessary parties) to the Consigned Items.
            EXPENSES. The Consignee shall bear all expenses for shipping the Consigned Items.
            <br/><br/>
            NO MODIFICATION UNLESS IN WRITING. No modification of this Agreement shall be valid unless in writing and agreed upon by both Parties.
            APPLICABLE LAW. This Agreement and the interpretation of its terms shall be governed by and construed in accordance with the laws of the State of [STATE] and subject to the exclusive jurisdiction of the federal and state courts located in [COUNTY], [STATE]
            IN WITNESS WHEREOF, each of the Parties has executed this Contract, both Parties by its duly authorized officer, as of the day and year set forth below.
            <br/><br/>
            [CONSIGNOR]
            _________________________________ ______________
            [NAME] DATE
            <br/>
            [CONSIGNEE]
            _________________________________ ______________
            [NAME] DATE
        '''
        return agreement_terms
    
    agreement_terms = fields.Html(
        string='Agreement Terms',
        default=get_agreement_term_deatils
    )
    is_consignment = fields.Boolean(
        string='Is Consignment Order',
    )

#    @api.multi #odoo13
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.is_consignment:
                for line in order.order_line:
                    line.product_id.sudo().write({
                        'purchase_order_line_id': line.id,
                        # 'total_available_qty': line.product_qty,
                        # 'purchase_qty': line.product_qty,
                        'purchase_price': line.price_unit,
                        # 'purchase_price_total': line.price_subtotal,
                    })
        return res

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        if self.is_consignment:
            res.update({
                'owner_id': self.partner_id.id,
                'is_consignment': self.is_consignment
            })
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_consignment = fields.Boolean(
        string='Is Consignment',
        related='order_id.is_consignment',
    )
