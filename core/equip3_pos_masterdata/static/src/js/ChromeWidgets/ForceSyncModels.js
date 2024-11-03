odoo.define('equip3_pos_masterdata.ForceSyncModels', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PosProductTemplate = require('equip3_pos_masterdata.PosProductTemplate');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const time = require('web.time');
    const {useState} = owl;

    class ForceSyncModels extends PosComponent {
        constructor() {
            super(...arguments);

            this.sync_state = useState({ 
                promotions: '',
            });
            this.warning_message = useState({ state: 'hidden' });
        }

        _warning_message1(){
            return this.env._t('Cannot close, There are still process on going');
        }
        
        close_warning_message(ev){
            $(ev.target).addClass('oe_hidden');
        }
        

        async close(ev) {
            let $popup = $(ev.target).closest('.popup');
            let in_process = false;
            for(let state in this.sync_state){
                if( this.sync_state[state] == 'connecting' ){
                    in_process = true;
                    break;
                }
            }
            if(in_process){
                $popup.find('.sync-models-list-warning').text(this._warning_message1());
                $popup.find('.sync-models-list-warning').removeClass('oe_hidden');
            }else{
                this.trigger('close-popup');
            }
        }

        async sync(type){
            if(type == 'promotions'){
                this.syncPromotions();
            }
        }

        async syncPromotions(){
            let self = this;
            if(self.sync_state.promotions == 'connecting'){
                return;
            }
            let vals = {
                'pos_config_id': self.env.pos.config.id,
                'pos.promotion': self.env.pos.db.write_date_by_model['pos.promotion'],
                'promotion_ids': self.env.pos.promotion_ids,
                'force_sync': true,
            }
            console.log('[syncPromotions] ~ vals: ', vals)
             
            let args = [[], vals];
            self.sync_state.promotions = 'connecting';
            let results = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_promotion', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncPromotions] ~ Server Offline')
                } else {
                    console.error('[syncPromotions] ~ Error 403')
                }
                self.sync_state.promotions = 'error';
                return null;
            });
            
            if (results != null) {
                this.remove_deleted_promotion_and_childs(results);

                if(results['pos.promotion'].length){
                    self.env.pos.sync_models = true;
                    let promotions = results['pos.promotion']; 
                    self.env.pos.indexed_db.write('pos.promotion', promotions);
                    self.env.pos.save_results('pos.promotion', promotions);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.discount.order'].length){
                    self.env.pos.sync_models = true;
                    var discounts = results['pos.promotion.discount.order'];
                    self.env.pos.indexed_db.write('pos.promotion.discount.order', discounts);
                    self.env.pos.save_results('pos.promotion.discount.order', discounts);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.discount.category'].length){
                    self.env.pos.sync_models = true;
                    var discounts_category = results['pos.promotion.discount.category'];
                    self.env.pos.indexed_db.write('pos.promotion.discount.category', discounts_category);
                    self.env.pos.save_results('pos.promotion.discount.category', discounts_category);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.discount.quantity'].length){
                    self.env.pos.sync_models = true;
                    var discounts_quantity = results['pos.promotion.discount.quantity'];
                    self.env.pos.indexed_db.write('pos.promotion.discount.quantity', discounts_quantity);
                    self.env.pos.save_results('pos.promotion.discount.quantity', discounts_quantity);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.gift.condition'].length){
                    self.env.pos.sync_models = true;
                    var gift_conditions = results['pos.promotion.gift.condition'];
                    self.env.pos.indexed_db.write('pos.promotion.gift.condition', gift_conditions);
                    self.env.pos.save_results('pos.promotion.gift.condition', gift_conditions);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.gift.free'].length){
                    self.env.pos.sync_models = true;
                    var gifts_free = results['pos.promotion.gift.free'];
                    self.env.pos.indexed_db.write('pos.promotion.gift.free', gifts_free);
                    self.env.pos.save_results('pos.promotion.gift.free', gifts_free);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.discount.condition'].length){
                    self.env.pos.sync_models = true;
                    var discount_conditions = results['pos.promotion.discount.condition'];
                    self.env.pos.indexed_db.write('pos.promotion.discount.condition', discount_conditions);
                    self.env.pos.save_results('pos.promotion.discount.condition', discount_conditions);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.discount.apply'].length){
                    self.env.pos.sync_models = true;
                    var discounts_apply = results['pos.promotion.discount.apply'];
                    self.env.pos.indexed_db.write('pos.promotion.discount.apply', discounts_apply);
                    self.env.pos.save_results('pos.promotion.discount.apply', discounts_apply);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.price'].length){
                    self.env.pos.sync_models = true;
                    var prices = results['pos.promotion.price'];
                    self.env.pos.indexed_db.write('pos.promotion.price', prices);
                    self.env.pos.save_results('pos.promotion.price', prices);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.selected.brand'].length){
                    self.env.pos.sync_models = true;
                    var promotion_lines = results['pos.promotion.selected.brand'];
                    self.env.pos.indexed_db.write('pos.promotion.selected.brand', promotion_lines);
                    self.env.pos.save_results('pos.promotion.selected.brand', promotion_lines);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.tebus.murah.selected.brand'].length){
                    self.env.pos.sync_models = true;
                    var promotion_lines = results['pos.promotion.tebus.murah.selected.brand'];
                    self.env.pos.indexed_db.write('pos.promotion.tebus.murah.selected.brand', promotion_lines);
                    self.env.pos.save_results('pos.promotion.tebus.murah.selected.brand', promotion_lines);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.special.category'].length){
                    self.env.pos.sync_models = true;
                    var promotion_lines = results['pos.promotion.special.category'];
                    self.env.pos.indexed_db.write('pos.promotion.special.category', promotion_lines);
                    self.env.pos.save_results('pos.promotion.special.category', promotion_lines);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.specific.product'].length){
                    self.env.pos.sync_models = true;
                    var promotion_lines = results['pos.promotion.specific.product'];
                    self.env.pos.indexed_db.write('pos.promotion.specific.product', promotion_lines);
                    self.env.pos.save_results('pos.promotion.specific.product', promotion_lines);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.multi.buy'].length){
                    self.env.pos.sync_models = true;
                    var multi_buy = results['pos.promotion.multi.buy'];
                    self.env.pos.indexed_db.write('pos.promotion.multi.buy', multi_buy);
                    self.env.pos.save_results('pos.promotion.multi.buy', multi_buy);
                    self.env.pos.sync_models = false;
                }

                if(results['pos.promotion.tebus.murah'].length){
                    self.env.pos.sync_models = true;
                    var tebus_murah = results['pos.promotion.tebus.murah'];
                    self.env.pos.indexed_db.write('pos.promotion.tebus.murah', tebus_murah);
                    self.env.pos.save_results('pos.promotion.tebus.murah', tebus_murah);
                    self.env.pos.sync_models = false;
                }
                if(results['pos.promotion.multilevel.condition'].length){
                    self.env.pos.sync_models = true;
                    var multilevel_condition = results['pos.promotion.multilevel.condition'];
                    self.env.pos.indexed_db.write('pos.promotion.multilevel.condition', multilevel_condition);
                    self.env.pos.save_results('pos.promotion.multilevel.condition', multilevel_condition);
                    self.env.pos.sync_models = false;
                }
                if(results['pos.promotion.multilevel.gift'].length){
                    self.env.pos.sync_models = true;
                    var multilevel_gift = results['pos.promotion.multilevel.gift'];
                    self.env.pos.indexed_db.write('pos.promotion.multilevel.gift', multilevel_gift);
                    self.env.pos.save_results('pos.promotion.multilevel.gift', multilevel_gift);
                    self.env.pos.sync_models = false;
                }
            }

            if(self.sync_state.promotions == 'error'){
                return false;
            }
            self.sync_state.promotions = 'done';
        }

        remove_deleted_promotion_and_childs(results){
            let self = this;
            let models = results.existing_ids_of_promotion_and_childs;
            if(!models){
                return false;
            }
            let promotion_models = self.env.pos.promotion_models;
            if(!promotion_models){
                return false;
            }
            for (let model in models){
                let existing_record_ids = models[model]; // in database
                let current_record_ids = promotion_models[model]; // in local browser
                let deleted_record_ids = [];
                if (existing_record_ids && current_record_ids) {
                    deleted_record_ids = current_record_ids.filter((id)=>existing_record_ids.includes(id)==false);
                }

                if(deleted_record_ids.length){
                    console.log('[syncPromotions] ~ Start removing ' + model + ' in IndexedDB', deleted_record_ids);
                    self.env.pos.indexed_db.unlink_data_by_ids(model, deleted_record_ids);

                    if (model == 'pos.promotion') {
                        if(self.env.pos.promotions){
                            self.env.pos.promotions = self.env.pos.promotions.filter((p)=>deleted_record_ids.includes(p.id)==false);
                        }
                        if(self.env.pos.promotion_by_id){
                            for (let deleted_id of deleted_record_ids) {
                                delete self.env.pos.promotion_by_id[deleted_id]; 
                            }
                        }
                        if(self.env.pos.promotion_ids){
                            self.env.pos.promotion_ids = self.env.pos.promotion_ids.filter((id)=>deleted_record_ids.includes(id)==false);
                        }
                        self.env.pos.promotion_models['pos.promotion'] = self.env.pos.promotion_ids;
                    }
                    if (model == 'pos.promotion.discount.order'){
                        if (self.env.pos.promotion_discount_order_by_id){
                            for (let deleted_id of deleted_record_ids) {
                                delete self.env.pos.promotion_discount_order_by_id[deleted_id]; 
                            }
                        }
                        if (self.env.pos.promotion_discount_order_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_discount_order_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.discount.category'){
                        if (self.env.pos.pos_disc_categ_new){
                            this.update_existing_record_by_object(
                                self.env.pos.pos_disc_categ_new,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.gift.condition'){
                        if (self.env.pos.promotion_gift_condition_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_gift_condition_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.gift.free'){
                        if (self.env.pos.promotion_gift_free_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_gift_free_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.discount.condition'){
                        if (self.env.pos.promotion_discount_condition_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_discount_condition_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.discount.apply'){
                        if (self.env.pos.promotion_discount_apply_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_discount_apply_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.price'){
                        if (self.env.pos.promotion_price_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_price_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.special.category'){
                        if (self.env.pos.promotion_special_category_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_special_category_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.selected.brand'){
                        if (self.env.pos.promotion_selected_brands){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_selected_brands,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.tebus.murah.selected.brand'){
                        if (self.env.pos.promotion_tebus_murah_selected_brands){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_tebus_murah_selected_brands,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.specific.product'){
                        if (self.env.pos.promotion_specific_product_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_specific_product_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.multi.buy'){
                        if (self.env.pos.multi_buy_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.multi_buy_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.tebus.murah'){
                        if (self.env.pos.promotion_tebus_murah_product_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_tebus_murah_product_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.multilevel.condition'){
                        if (self.env.pos.promotion_multilevel_condition_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_multilevel_condition_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.multilevel.gift'){
                        if (self.env.pos.promotion_multilevel_gift_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_multilevel_gift_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    console.log('[syncPromotions] ~ Finish removing ' + model + ' in IndexedDB');
                }
            }
        }

        update_existing_record_by_object(object, existing_record_ids){
            for (let object_id in object){
                object[object_id] = object[object_id].filter((o)=>existing_record_ids.includes(o.id)==true);
            }
        }

    }

    ForceSyncModels.template = 'ForceSyncModels';
    Registries.Component.add(ForceSyncModels);
    return ForceSyncModels;
});
