odoo.define('equip3_pos_indo_numpad.ExtendedNumberBuffer', function(require) {
    'use strict';

    const { Component } = owl;
    const { EventBus } = owl.core;
    const { onMounted, onWillUnmount, useExternalListener } = owl.hooks;
    const { _t } = require('web.core');
    const { Gui } = require('point_of_sale.Gui');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');

    const INPUT_KEYS = new Set(
        ['Delete', 'Backspace', '+1', '+2', '+5', '+10', '+20', '+50','+1000', '+10000', '+50000', ].concat('0123456789+-.,'.split(''))
    );
    const CONTROL_KEYS = new Set(['Enter', 'Esc']);
    const ALLOWED_KEYS = new Set([...INPUT_KEYS, ...CONTROL_KEYS]);


    NumberBuffer._onInput = function (keyAccessor) {   
        return () => {
            if (this.eventsBuffer.length <= 2) {
                for (let event of this.eventsBuffer) {
                    if (!ALLOWED_KEYS.has(keyAccessor(event))) {
                        this.eventsBuffer = [];
                        return;
                    }
                }

                for (let event of this.eventsBuffer) {
                    this._handleInput(keyAccessor(event));
                    event.preventDefault();
                    event.stopPropagation();
                }
            }
            this.eventsBuffer = [];
        };
    }


    NumberBuffer._handleInput = function (key) {   
        if (key === 'Enter' && this.config.triggerAtEnter) {
                this.component.trigger(this.config.triggerAtEnter, this.state);
            } else if (key === 'Esc' && this.config.triggerAtEsc) {
                this.component.trigger(this.config.triggerAtEsc, this.state);
            } else if (INPUT_KEYS.has(key)) {
                this._updateBuffer(key);
                if (this.config.triggerAtInput)
                    this.component.trigger(this.config.triggerAtInput, { buffer: this.state.buffer, key });
            }
    }




});

