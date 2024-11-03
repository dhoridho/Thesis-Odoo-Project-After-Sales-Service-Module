odoo.define('equip3_pos_online_grabfood.OnlineOrderReadyTimePopup', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const core = require('web.core');
    const _t = core._t;
    const {Gui} = require('point_of_sale.Gui');
    const {useState} = owl;


    class OnlineOrderReadyTimePopup extends PosComponent {
        constructor() {
            super(...arguments);
        }
        cancel() {
            this.trigger('close-popup');
        }
        async confirm() {
            let self = this;
            let has_error = [];
            let $popup = $('.popup.online-order-ready-time-popup'); 
            let payload = {
                'duration': $popup.find('[name="duration"]').val(),
            } 
			this.props.resolve({ confirmed: true, payload: payload });
            this.trigger('close-popup');
		}
    }

    OnlineOrderReadyTimePopup.template = 'OnlineOrderReadyTimePopup';
    OnlineOrderReadyTimePopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Change Estimation Ready Time (Duration)',
    };
    Registries.Component.add(OnlineOrderReadyTimePopup);

    return OnlineOrderReadyTimePopup;
});
