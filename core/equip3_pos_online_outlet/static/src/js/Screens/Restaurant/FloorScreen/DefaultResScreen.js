odoo.define('equip3_pos_online_outlet.DefaultResScreen', function (require) {
    'use strict';

    const DefaultResScreen = require('equip3_pos_masterdata.DefaultResScreen');
    const Registries = require('point_of_sale.Registries');

    const DefaultResScreenExt = (DefaultResScreen) =>
     class extends DefaultResScreen {
        constructor() {
            super(...arguments)
        }
        
        showOnlineOrder() {
            if(this.env.pos.selected_order_method != 'online-order'){
                this.clearCart();
            }
            if(this.env.pos.tables){
                var table = this.env.pos.tables[0]; 
                this.env.pos.set_table(table);   
            }
            this.env.pos.selected_order_method = 'online-order';
            $('.back-to-home').show();
            // $('.pos').attr('data-selected-order-method','online-order');  
            // $('.pos > .pos-content').attr('data-selected-order-method','online-order');  
            this.showScreen('ProductScreen', {selected_order_method: 'online-order'});
            this.showScreen('OnlineOrderList',{
                order: null,
                selectedClient: null,
                close_screen_button: true,
                selected_order_method: 'online-order',
            });
        }
        
    }

    Registries.Component.extend(DefaultResScreen, DefaultResScreenExt);
    return DefaultResScreenExt;

});