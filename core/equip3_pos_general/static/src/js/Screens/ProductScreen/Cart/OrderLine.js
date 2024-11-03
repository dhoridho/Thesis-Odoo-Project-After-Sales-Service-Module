odoo.define('equip3_pos_general.Orderline', function (require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl.hooks;
    const {posbus} = require('point_of_sale.utils');

    const GeneralOrderLine = (Orderline) => class extends Orderline {
        constructor() {
            super(...arguments);
        }

        get getSuggestionNotActive() {
            if (this.props.line.product.cross_selling && this.env.pos.cross_items_by_product_tmpl_id != undefined && this.env.pos.cross_items_by_product_tmpl_id[this.props.line.product.product_tmpl_id]) {
                return false;
            }else{
                return true;
            }
        }

        async showSuggestProduct(line) {
            const selectedOrder = this.env.pos.get_order();
            if (selectedOrder) {
                selectedOrder.suggestItems(line.product)
            }
        }
        async setUomPopup() {
            const selectedOrder = this.env.pos.get_order()
            const selecteLine = selectedOrder.get_selected_orderline()

            let uom_items = this.env.pos.uoms_prices_by_product_tmpl_id[selecteLine.product.product_tmpl_id];
            if (uom_items) {
                let list = uom_items.map((u) => ({
                    id: u.id,
                    label: u.uom_id[1],
                    item: u
                }));
                let {confirmed, payload: unit} = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select Unit of Measure for : ') + selecteLine.product.display_name,
                    list: list
                })
                if (confirmed) {
                    selecteLine.change_unit(unit);
                }
            }
        }
    }

    Registries.Component.extend(Orderline, GeneralOrderLine);
    Orderline.template = 'RetailOrderline2';
    return GeneralOrderLine;
});
