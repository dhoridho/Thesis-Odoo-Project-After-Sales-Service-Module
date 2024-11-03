/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_keyboard_shortcut.pos_keyboard_shortcut', function(require){
"use strict";
    var models = require('point_of_sale.models');        
    const Registries = require('point_of_sale.Registries');
    const Chrome = require('point_of_sale.Chrome');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const NumberBufferShortcut = require('point_of_sale.pos_keyboard_shortcut');

    models.load_models([{
        model:'pos.keyboard.shortcuts',
        field: [],
        loaded: function(self, result){
            if(self.config.enable_shortcuts && self.config.select_shortcut){
                self.db.shortcuts_by_id = {};
                _.each(result, function(shortcut){
                    if (self.config.select_shortcut[0] == shortcut.id){
                        self.db.shortcuts_by_id[shortcut.id] = shortcut;
                    }
                });
            }
        }
    },{
        model:'pos.payment.method.key',
        field: [],
        loaded: function(self, result){
            if(self.config.enable_shortcuts && self.config.select_shortcut){
                var shortcut = self.db.shortcuts_by_id[self.config.select_shortcut[0]]
                if (shortcut){
                    self.journal_key = [];
                    self.db.journal_key_by_id = {}
                    _.each(result, function(journal){
                        if(shortcut.payment_methods.includes(journal.id)){
                            self.db.journal_key_by_id[journal.id] = journal;
                            self.journal_key.push(journal)
                        }
                    });
                }
            }
        }
    }], {'after': 'pos.config'});

    // Inherit Chrome----------------
    const PosResChrome = (Chrome) =>
		class extends Chrome {
            constructor() {
                super(...arguments);
                NumberBufferShortcut.activate();
            }
        };
    Registries.Component.extend(Chrome, PosResChrome);

    // Inherit ProductScreen----------------
    const PosResProductScreen = (ProductScreen) =>
		class extends ProductScreen {
            constructor() {
                super(...arguments);
                NumberBufferShortcut.use({
                    triggerAtInput: 'update-page',
                }); 
            }
        }
    Registries.Component.extend(ProductScreen, PosResProductScreen);

});