odoo.define('equip3_pos_masterdata.KitchenOrderLineDetail', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class KitchenOrderLineDetail extends PosComponent {
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
        display_name(name){
            if(this.env.pos.config && this.env.pos.config.display_product_name_without_product_code){
                return name.replace(/[\[].*?[\]] */, '');
            }
            return name
        }
    }
    KitchenOrderLineDetail.template = 'KitchenOrderLineDetail';

    Registries.Component.add(KitchenOrderLineDetail);

    return KitchenOrderLineDetail;
});