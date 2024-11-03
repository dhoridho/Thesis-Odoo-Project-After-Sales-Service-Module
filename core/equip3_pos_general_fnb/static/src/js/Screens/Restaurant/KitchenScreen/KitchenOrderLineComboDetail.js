odoo.define('equip3_pos_general_fnb.KitchenOrderLineComboDetail', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const {useListener} = require('web.custom_hooks');

    class KitchenOrderLineComboDetail extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = {
                startTime: this.props.order.request_time || new Date().getTime(),
            };
        } 

        get isHighlighted() {
            if (this.env.pos.config.screen_type == 'cashier') {
                return (this.props.line.selected && !['Removed', 'Paid', 'Cancelled', 'Kitchen Requesting Cancel'].includes(this.props.line.state)) || (this.props.line.state == 'Ready Transfer')
            } else {
                return (this.props.line.selected)
            }

        }

        get isCancelled() {
            return ['Removed', 'Paid', 'Cancelled', 'Kitchen Requesting Cancel'].includes(this.props.line.state)
        }

        get allowDisplay () {
            if(this.props.option.kot_checked){
                return false;
            }
            if(this.env.pos.config.display_all_product){
                return true
            }
            if(this.env.pos.config.limit_categories){
                var display = this.env.pos.db.is_product_in_category(this.env.pos.config.iface_available_categ_ids, this.props.line.id);
                if (display) {
                    return true
                } else {
                    return false
                }
            }
            else{
                return true
            }
        }

        get isSucceed() {
            if (['Done', 'Ready Transfer'].includes(this.props.line.state)) return true
            else return false
        }

        get warningWaitingTimeDetail() {
            var diff = new Date().getTime() - this.state.startTime;
            var msec = diff;
            var hh = `0${Math.floor(msec / 1000 / 60 / 60)}`;
            msec -= hh * 1000 * 60 * 60;
            var mm = `0${Math.floor(msec / 1000 / 60)}`;
            if ((Math.floor(msec / 1000 / 60) >= this.env.pos.config.period_minutes_warning)) {
                return true
            } else {
                return false
            }
        }

        display_name(rec){
            let self = this;
            let display_name = rec.product_id[1];
            if(self.env.pos.config && self.env.pos.config.display_product_name_without_product_code){
                return display_name.replace(/[\[].*?[\]] */, '');
            }
            return display_name;
        }

        get_pos_combo_options_display(option) {
            let self = this;
            let html = '';
            if(option.bom_components){
                let label = self.display_name(option);
                html += ' <div class="combo-option">'
                let html_com = '';
                html_com += ' <div class="bom_components"> ';
                let bom_components = option.bom_components;
                bom_components.sort(function(a, b){ return b.is_extra?1:-1; });

                for (var i = bom_components.length - 1; i >= 0; i--) {
                    let com = bom_components[i];
                    let product_name = self.display_name(com);
                    let product_qty = com.product_qty;
                    if(com.is_extra){
                        if(com.checked){
                            html_com += ' <div class="div-component"> '+ product_qty + 'X Extra ' + product_name + '</div> ';
                        }
                    }else{
                        if(!com.checked){
                            html_com += ' <div class="div-component">No ' + product_name + '</div> ';
                        }
                    }
                }
                if(option.bom_component_notes){
                    html_com += ' <div class="bom_component_notes">Note: ' + option.bom_component_notes + '</div> ';
                }

                html_com += ' </div> ';
                html += html_com;
            }


            html += ' </div> ';
            return html;
        }

    }

    KitchenOrderLineComboDetail.template = 'KitchenOrderLineComboDetail';
    Registries.Component.add(KitchenOrderLineComboDetail);
    return KitchenOrderLineComboDetail;
});