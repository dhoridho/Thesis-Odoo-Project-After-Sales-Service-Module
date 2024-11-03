odoo.define('equip3_pos_online_outlet.OnlineOutletStatus', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const framework = require('web.framework');
    const { useState, useExternalListener } = owl.hooks;
    let checkStateInterval = null;

    class OnlineOutletStatus extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                showOptions: false,
            });
            this.online_state = 'close';
        }

        mounted() {
            let self = this; 
            super.mounted();
            this.getStateFromBackEnd();

            clearInterval(checkStateInterval);
            checkStateInterval = setInterval(function () {
                self.getStateFromBackEnd();
            }, 6000);
        }

        willUnmount() {
            super.willUnmount();
            clearInterval(checkStateInterval);
        }

        async getStateFromBackEnd() {
            await this.env.pos.getOnlineOutlet();
            let prev_online_state = this.online_state;
            let outlet = this.env.pos.db.get_online_outlet();
            this.online_state = outlet.state;
            if(this.online_state != prev_online_state){
                this.render();
            }
        }
        async changeOutletState(state) {
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Confirmation'),
                body: 'Are you sure want to change this outlet status?',
            });
            if (confirmed) {
                framework.blockUI();

                let outlet = this.env.pos.db.get_online_outlet();
                await this.rpc({
                    model: 'pos.online.outlet',
                    method: 'change_online_outlet_state',
                    args: [outlet.id],
                    context: {
                        state: state
                    }
                });
                framework.unblockUI();
            }
        }

        getState() {
            return this.online_state;
        }

        get isHidden() {
            return false;
        }
    }

    OnlineOutletStatus.template = 'OnlineOutletStatus';
    Registries.Component.add(OnlineOutletStatus);
    return OnlineOutletStatus;
});