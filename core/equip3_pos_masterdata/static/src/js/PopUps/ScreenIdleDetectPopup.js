odoo.define('equip3_pos_masterdata.ScreenIdleDetectPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl

    class ScreenIdleDetectPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.sync = useState({ state: '' });
            this.state = useState({ error_message: '' , message:'' });
            this.state.message = this.env._t("You'are being timed out due to inactivity. Please choose to Stay or Close Pos Screen.");
        }

        async pushOrders() {
            let self = this;
            if (self.sync.state == 'connecting') {
                return false;
            }

            self.sync.state = 'connecting';
            self.state.error_message = '';
            const pingServer = await self.env.pos._check_connection();
            if (!pingServer) {
                self.state.error_message = self.env._t('Your Internet or Hashmicro Server Offline');
                self.sync.state = 'error';
                self.env.pos.stopScreenIdleDetect = false;
                return false;
            }
            self.sync.state = 'done';
            
            self.env.pos._turn_on_save_order_to_server();

            let orders = self.env.pos.db.get_orders();
            self.sync.state = 'connecting';
            for (let order of orders){
                let result = await self.env.pos.push_order_one(order.data.uid, { show_error: true });
                console.warn('[pushOrders] - result:', result)
            }
            self.sync.state = 'done';
        }
 
        async action_close(){
            let self = this;
            await this.pushOrders();
            if (self.sync.state == 'done') {
                self.sync.state = 'closingpos';
                self.state.message = this.env._t('Closing POS Screen...');
                await this.env.pos.close_pos();
            }
        }

        async action_stay(){
            let self = this;
            await this.pushOrders();
            if (self.sync.state == 'done') {
                super.confirm();
            }
        }
    }
    
    ScreenIdleDetectPopup.template = 'ScreenIdleDetectPopup';
    ScreenIdleDetectPopup.defaultProps = {
        closeText: 'Close',
        stayText: 'Stay (in Pos Screen)',
        title: 'Session Timeout',
        messageText: "You'are being timed out due to inactivity. Please choose to Stay or Close Pos Screen.",
    };
    Registries.Component.add(ScreenIdleDetectPopup);
    return ScreenIdleDetectPopup;
});
