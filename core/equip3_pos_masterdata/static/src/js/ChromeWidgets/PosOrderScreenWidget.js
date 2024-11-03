odoo.define('equip3_pos_masterdata.PosOrderScreenWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class PosOrderScreenWidget extends PosComponent {
        async onClick() {
            if(this.env.pos.db.pos_load_data_from_pos_cache_sdk){
                await this.env.pos.syncPOSOrdersFromPosCache(false); 
            } else {
                await this.env.pos.syncPOSOrders(false); 
            }
            this.showTempScreen( 'PosOrderScreen',{
                order: null,
                selectedClient: null,
                close_screen_button: true
            });
        }

        mounted() {
            posbus.on('reload-orders', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-orders', this, null);
            
        }

        get isHidden() {
            if (!this.env || !this.env.pos || !this.env.pos.config || (this.env && this.env.pos && this.env.pos.config && !this.env.pos.config.pos_orders_management)) {
                return true
            } else {
                return false
            }
        }

        get count() {
            var domain_state_not_include = ['cancel']
            if (this.env.pos && this.env.pos.db && this.env.pos.db.order_by_id) {
                if(this.env.pos.config.order_loading_options=='n_days'){
                    var today = new Date();
                    var validation_date = new Date(today.setDate(today.getDate()-this.env.pos.config.number_of_days));
                    this.order_history = this.env.pos.db.pos_orders.filter((o) => new Date(o.date_order) >= validation_date && !domain_state_not_include.includes(o.state) && o.config_id[0]==this.env.pos.config.id)
                }
                else if(this.env.pos.config.order_loading_options == 'current_session') {
                    var session_active_ids = []
                    var session_active = this.env.pos.pos_sessions.filter((o) => o.config_id[0]==this.env.pos.config.id && ['opened','opening_control'].includes(o.state))
                    for(var ii = 0, len = session_active.length; ii < len; ii++){
                        session_active_ids.push(session_active[ii].id)
                    }
                    this.order_history = this.env.pos.db.pos_orders.filter((a) => session_active_ids.includes(a.session_id[0])  && !domain_state_not_include.includes(a.state) )
                }
                else{
                    this.order_history = this.env.pos.db.pos_orders.filter((o) => !domain_state_not_include.includes(o.state) && o.config_id[0]==this.env.pos.config.id)
                }
                return this.order_history.length
            } else {
                return 0
            }
        }
    }

    PosOrderScreenWidget.template = 'PosOrderScreenWidget';

    Registries.Component.add(PosOrderScreenWidget);

    return PosOrderScreenWidget;
});
