odoo.define('equip3_pos_cashbox.ManageCashButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');
    const session = require('web.session');

    class ManageCashButton extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        async onClick() {
            if (this.env.pos.config.is_cash_management_with_validation) {
                let validate = await this.env.pos._validate_action(this.env._t('Manager Approval'));
                if (!validate) {
                    return false;
                }
            }

            let {confirmed, payload: values} = await Gui.showPopup('ManageCashPopup');
            if(confirmed){
                let _action = values.action;
                let pos_session_id = this.env.pos.config.current_session_id[0];
                let result = await this.rpc({
                    model: 'pos.session',
                    method: 'action_save_cashbox',  
                    args: [[pos_session_id], values],
                });
                console.log('Save Cashbox result:\n', result)
                if(result.status == 'success'){
                    let message = 'Successfully Put Money In';
                    if(_action == 'out') {
                        message = 'Successfully Take Money Out';
                    }
                    this.env.pos.alert_message({
                        title: this.env._t('Success'),
                        body: this.env._t(message)
                    });
                }
            }
        }

        mounted() {
            posbus.on('reload-manage-cash-button', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-manage-cash-button', this, null);
        }

        get isHidden() {
            return false;
        }
    }

    ManageCashButton.template = 'ManageCashButton';
    ProductScreen.addControlButton({
        component: ManageCashButton,
        condition: function() {
            return this.env.pos.config.bnk_cash_control;
        },
    });
    Registries.Component.add(ManageCashButton);
    return ManageCashButton;
});