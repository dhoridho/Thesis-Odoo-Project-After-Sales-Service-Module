odoo.define('pos_retail.pos_restart_data', function (require){
"use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');
    var _t = core._t;

    var pos_restart_data = AbstractAction.extend({
        contentTemplate: "pos_restart_data_action",
        hasControlPanel: !1,
        events: {
            "click .btn-pos-remove-indexdb": "_onPosRemoveIndexDB",
            "click .btn-pos-reinstall-poscalllog": "_openDialog",
            "click .btn-cancel": "_closePopup",
        },
        _closePopup: function(ev){
            let $target = this.$el.closest('.modal-content').find('[data-dismiss="modal"]');
            $target.click();
        },
        // Clear Storage & Remove IndexDB
        removeIndexDb: function(){
            localStorage.clear();
            let database_template = session.db;
            for (let i = 0; i < 200; i++) {
                indexedDB.deleteDatabase(database_template + '_' + i);
                console.log('removed db: ' + database_template + '_' + i);
            }
            indexedDB.deleteDatabase('POS-DB');
            
            localStorage.removeItem('pos_state_load_models');
        },
        _onPosRemoveIndexDB: function(ev){ 
            this.removeIndexDb();
            this._closePopup();
        },
        _openDialog: function () {
            let self = this;
            var buttons = [
                {
                    text: _t("Confirm"),
                    classes: 'btn-primary',
                    close: true,
                    click : function(){
                        self._onPosReinstallPosCallLog();
                    }
                },
                {
                    text: _t("Cancel"),
                    close: true,
                },
            ];

            return new Dialog(this, {
                size: 'medium',
                buttons: buttons,
                $content: $('<div>', {
                    html: 'Are you sure you want to Reinstall Log Data?',
                }),
                title: _t("Warning"),
            }).open();
        },
        _onPosReinstallPosCallLog: async function(){
            let self = this;
            let $popup = this.$el.closest('.modal-content');
            $popup.addClass('installing_data');

            await self.api_install_datas('product.product');
            await self.api_install_datas('product.template');
            await self.api_install_datas('product.template.barcode');
            await self.api_install_datas('product.pricelist.item');
            await self.api_install_datas('res.partner');
            await self.api_install_datas('stock.production.lot');
            await self.api_install_datas('stock.quant');
            await self.api_install_datas('product.brand');
            await self.api_install_datas('pos.voucher');

            // Start Promotions
            await self.api_install_datas('pos.promotion');
            await self.api_install_datas('pos.promotion.discount.order');
            await self.api_install_datas('pos.promotion.discount.category');
            await self.api_install_datas('pos.promotion.discount.quantity');
            await self.api_install_datas('pos.promotion.gift.condition');
            await self.api_install_datas('pos.promotion.gift.free');
            await self.api_install_datas('pos.promotion.discount.condition');
            await self.api_install_datas('pos.promotion.discount.apply');
            await self.api_install_datas('pos.promotion.special.category');
            await self.api_install_datas('pos.promotion.selected.brand');
            await self.api_install_datas('pos.promotion.tebus.murah.selected.brand');
            await self.api_install_datas('pos.promotion.specific.product');
            await self.api_install_datas('pos.promotion.tebus.murah');
            await self.api_install_datas('pos.promotion.multi.buy');
            await self.api_install_datas('pos.promotion.multilevel.condition');
            await self.api_install_datas('pos.promotion.multilevel.gift');
            await self.api_install_datas('pos.promotion.price');
            // End Promotions
            
            await self.api_install_datas('pos.order');
            await self.api_install_datas('pos.order.line');

            await self.api_install_datas('account.move'); 
            await self.api_install_datas('account.move.line'); 

            this.removeIndexDb();

            $popup.addClass('done');
            $popup.find('button.btn-cancel').addClass('btn-primary').removeClass('btn-default');
            self.setLoadingMessage(_t('Installing Model is Done'));
        },
        setLoadingMessage: function(message){
            let $popup = this.$el.closest('.modal-content');
            $popup.find('.loading_message').text(message);
        },
        api_install_datas: async function(model_name) {
            let self = this;

            let model_max_id = 0;
            let max_load = 9999;
            let next_load = 10000;
            let first_load = 10000;

            await rpc.query({
                model: 'pos.cache.database',
                method: 'get_model_max_id',
                args: [null, model_name]
            }).then(function (result) {
                model_max_id = result;
            });
            console.log('[api_install_datas] model_max_id: ', model_max_id)

            let installed = new Promise(function (resolve, reject) {
                function installing_data(model_name, min_id, max_id) {
                    self.setLoadingMessage(_t('Installing Model: ' + model_name + ' from ID: ' + min_id + ' to ID: ' + max_id));
                    if (min_id == 0) {
                        max_id = max_load;
                    }
                    rpc.query({
                        model: 'pos.cache.database',
                        method: 'install_data_from_backend',
                        args: [null, model_name, min_id, max_id]
                    }, {
                        shadow: true,
                        timeout: 1200000 // 20 minutes
                    }).then(function (result_count) {
                        console.log('[api_install_datas] ', model_name ,' result_count: ', result_count)
                        min_id += next_load;
                        if (result_count > 0) {
                            max_id += next_load;
                            installing_data(model_name, min_id, max_id);
                        } else {
                            if (max_id < model_max_id) {
                                max_id += next_load;
                                installing_data(model_name, min_id, max_id);
                            } else {
                                resolve()
                            }
                        }
                    }, function (error) {
                        console.error('[installing_data] ERROR :\n', error.message.message);
                        reject(error)
                    })
                }

                installing_data(model_name, 0, first_load);
            });
            return installed;
        },
    });

    core.action_registry.add('pos_restart_data_tag', pos_restart_data);
    return pos_restart_data;
});