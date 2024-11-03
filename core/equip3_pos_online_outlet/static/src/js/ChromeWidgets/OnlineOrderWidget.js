odoo.define('equip3_pos_online_outlet.OnlineOrderWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');

    class OnlineOrderWidget extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        onClick() {
            this.showScreen('OnlineOrderList',{
                order: null,
                selectedClient: null,
                close_screen_button: true
            });
        }

        mounted() {
            posbus.on('reload-online-orders', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-online-orders', this, null);
        }

        get isHidden() {
            return false;
        }
    }

    OnlineOrderWidget.template = 'OnlineOrderWidget';
    ProductScreen.addControlButton({
        component: OnlineOrderWidget,
        condition: function() {
            if(this.env.pos.config.online_outlet_id){
                return true;
            }
            return false;
        },
    });
    Registries.Component.add(OnlineOrderWidget);
    return OnlineOrderWidget;
});