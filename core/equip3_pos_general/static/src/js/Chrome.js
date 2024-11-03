odoo.define('equip3_pos_general.Chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const CloseGeneralChrome = (Chrome) =>
        class extends Chrome {
            async _closePos() {
                // Immediate session closing
                return this._closePosScreen()
            }
            _onPlaySound({ detail: name }) {
                let src;
                if (name === 'error') {
                    // Blocking the error messsage sound
//                    src = "/point_of_sale/static/src/sounds/error.wav";
                } else if (name === 'bell') {
                    // src = "/point_of_sale/static/src/sounds/bell.wav";
                }
                this.state.sound.src = src;
            }
        }
    Registries.Component.extend(Chrome, CloseGeneralChrome);

    return CloseGeneralChrome;
});