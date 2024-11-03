odoo.define('equip3_pos_general.PosErrorMessagePopup', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const { useState } = owl.hooks;

    class PosErrorMessagePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ 'message':'', 'debug_message': '' })

            if(this.props.message){
                this.state.message = this.props.message.data.message;
                this.state.debug_message = this.props.message.data.debug;
            }
        }

        buttonViewDetail(){
            if(this.state.debug_message){
                $('#blob_error_download').click();
            }
        }

        get tracebackUrl() {
            const blob = new Blob([this.state.debug_message]);
            const URL = window.URL || window.webkitURL;
            return URL.createObjectURL(blob);
        }

        get tracebackFilename() {
            return `${this.env._t('error')} ${moment().format('YYYY-MM-DD-HH-mm-ss')}.txt`;
        }

        confirm(){
            super.confirm();
        }
    }

    PosErrorMessagePopup.template = 'PosErrorMessagePopup';
    PosErrorMessagePopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error with Traceback',
    };

    Registries.Component.add(PosErrorMessagePopup);
    return PosErrorMessagePopup;
});