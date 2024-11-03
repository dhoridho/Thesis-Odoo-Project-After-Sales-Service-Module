odoo.define('equip3_pos_masterdata.indexedDB', function (require) {
    "use strict";

    var indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB || window.shimIndexedDB;
    if (!indexedDB) {
        window.alert("Your browser doesn't support a stable version of IndexedDB.")
    }
    var Backbone = window.Backbone;

    var multi_database = Backbone.Model.extend({
        initialize: function (session) {
            this.session = session;
            this.data_by_model = {}
        },
        init: function (table_name, sequence) {
            var self = this;
            return new Promise(function (resolve, reject) {
                const request = indexedDB.open(self.session.db + '_' + sequence, 1);
                request.onerror = function (ev) {
                    reject(ev);
                };
                request.onupgradeneeded = function (ev) {
                    var db = ev.target.result;

                    var os_product = db.createObjectStore('product.product', {keyPath: "id"});
                    os_product.createIndex('bc_index', 'barcode', {unique: false});
                    os_product.createIndex('dc_index', 'default_code', {unique: false});
                    os_product.createIndex('name_index', 'name', {unique: false});

                    var os_product_template = db.createObjectStore('product.template', {keyPath: "id"});
                    os_product_template.createIndex('bc_index', 'barcode', {unique: false});
                    os_product_template.createIndex('dc_index', 'default_code', {unique: false});
                    os_product_template.createIndex('name_index', 'name', {unique: false});

                    var os_product_template_barcode = db.createObjectStore('product.template.barcode', {keyPath: "id"});
                    os_product_template_barcode.createIndex('name_index', 'name', {unique: false});

                    var os_partner = db.createObjectStore('res.partner', {keyPath: "id"});
                    os_partner.createIndex('barcode_index', 'barcode', {unique: false});
                    os_partner.createIndex('mobile_index', 'mobile', {unique: false});
                    os_partner.createIndex('phone_index', 'phone', {unique: false});
                    os_partner.createIndex('email_index', 'email', {unique: false});

                    var os_lot = db.createObjectStore('stock.production.lot', {keyPath: "id"});
                    os_lot.createIndex('name_index', 'name', {unique: false});

                    var os_stock_quant = db.createObjectStore('stock.quant', {keyPath: "id"});
                    os_stock_quant.createIndex('name_index', 'display_name', {unique: false});

                    var os_product_brand = db.createObjectStore('product.brand', {keyPath: "id"});
                    os_product_brand.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_voucher = db.createObjectStore('pos.voucher', {keyPath: "id"});
                    os_pos_voucher.createIndex('number_index', 'number', {unique: false});

                    var os_pricelist = db.createObjectStore('product.pricelist.item', {keyPath: "id"});
                    os_pricelist.createIndex('name_index', 'name', {unique: false});

                    // Start Promotions
                    var os_pos_promotion = db.createObjectStore('pos.promotion', {keyPath: "id"});
                    os_pos_promotion.createIndex('name_index', 'name', {unique: false});

                    var os_pos_promotion_discount_order = db.createObjectStore('pos.promotion.discount.order', {keyPath: "id"});
                    os_pos_promotion_discount_order.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_discount_category = db.createObjectStore('pos.promotion.discount.category', {keyPath: "id"});
                    os_pos_promotion_discount_category.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_discount_quantity = db.createObjectStore('pos.promotion.discount.quantity', {keyPath: "id"});
                    os_pos_promotion_discount_quantity.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_gift_condition = db.createObjectStore('pos.promotion.gift.condition', {keyPath: "id"});
                    os_pos_promotion_gift_condition.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_gift_free = db.createObjectStore('pos.promotion.gift.free', {keyPath: "id"});
                    os_pos_promotion_gift_free.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_discount_condition = db.createObjectStore('pos.promotion.discount.condition', {keyPath: "id"});
                    os_pos_promotion_discount_condition.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_discount_apply = db.createObjectStore('pos.promotion.discount.apply', {keyPath: "id"});
                    os_pos_promotion_discount_apply.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_special_category = db.createObjectStore('pos.promotion.special.category', {keyPath: "id"});
                    os_pos_promotion_special_category.createIndex('name_index', 'display_name', {unique: false});


                    var os_pos_promotion_selected_brand = db.createObjectStore('pos.promotion.selected.brand', {keyPath: "id"});
                    os_pos_promotion_selected_brand.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_tebus_murah_selected_brand = db.createObjectStore('pos.promotion.tebus.murah.selected.brand', {keyPath: "id"});
                    os_pos_promotion_tebus_murah_selected_brand.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_specific_product = db.createObjectStore('pos.promotion.specific.product', {keyPath: "id"});
                    os_pos_promotion_specific_product.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_multi_buy = db.createObjectStore('pos.promotion.multi.buy', {keyPath: "id"});
                    os_pos_promotion_multi_buy.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_price = db.createObjectStore('pos.promotion.price', {keyPath: "id"});
                    os_pos_promotion_price.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_tebus_murah = db.createObjectStore('pos.promotion.tebus.murah', {keyPath: "id"});
                    os_pos_promotion_tebus_murah.createIndex('name_index', 'display_name', {unique: false});

                    var os_pos_promotion_multilevel_condition = db.createObjectStore('pos.promotion.multilevel.condition', {keyPath: "id"});
                    os_pos_promotion_multilevel_condition.createIndex('name_index', 'display_name', {unique: false});
                    
                    var os_pos_promotion_multilevel_gift = db.createObjectStore('pos.promotion.multilevel.gift', {keyPath: "id"});
                    os_pos_promotion_multilevel_gift.createIndex('name_index', 'display_name', {unique: false});
                    // End Promotions
                    
                    var os_posorder = db.createObjectStore('pos.order', {keyPath: "id"});
                    os_posorder.createIndex('name_index', 'name', {unique: false});
                    var os_posorderline = db.createObjectStore('pos.order.line', {keyPath: "id"});
                    os_posorderline.createIndex('name_index', 'name', {unique: false});

                    // Start Invoices
                    var os_account_move = db.createObjectStore('account.move', {keyPath: "id"});
                    os_account_move.createIndex('id_index', 'id', {unique: false});

                    var os_account_move_line = db.createObjectStore('account.move.line', {keyPath: "id"});
                    os_account_move_line.createIndex('id_index', 'id', {unique: false});
                    // End Invoices


                    db.createObjectStore('cached', {keyPath: "id"});
                };
                request.onsuccess = function (ev) {
                    var db = ev.target.result;
                    var transaction = db.transaction([table_name], "readwrite");
                    transaction.oncomplete = function () {
                        db.close();
                    };
                    if (!transaction) {
                        reject('Cannot create transaction with ' + table_name)
                    }
                    var store = transaction.objectStore(table_name);
                    if (!store) {
                        reject('Cannot get object store with ' + table_name)
                    }
                    resolve(store)
                };
            })
        },
        write: function (table_name, items, cached) {
            const self = this;
            let default_field_active_in_models = ['account.move', 'account.move.line'];
            items = _.filter(items, function (item) {
                if(default_field_active_in_models.includes(table_name)){
                    item['active'] = true;
                    return true;
                }
                return item['active'] == true;
            });
            let last_item = items[items.length - 1];

            // NOTE: need to check later! error when delete "store.delete(item)"
            // let items_to_delete = _.filter(items, function (item) {
            //     return item['deleted'] || item['removed'] 
            // });
            console.warn('updating table: ' + table_name + ' with total rows: ' + items.length)
            console.warn('updating table: last_item :', last_item)
            if(last_item){
                let max_id = last_item['id'];
                let sequence = Math.floor(max_id / 100000);
                if (cached) {
                    sequence = 0
                }
                this.init(table_name, sequence).then(function (store) {
                    var request = indexedDB.open(self.session.db + '_' + sequence, 1);
                    request.onsuccess = function (ev) {
                        var db = ev.target.result;
                        var transaction = db.transaction([table_name], "readwrite");
                        transaction.oncomplete = function () {
                            db.close();
                        };
                        if (!transaction) {
                            return;
                        }
                        var store = transaction.objectStore(table_name);
                        if (!store) {
                            return;
                        }
                        _.each(items, function (item) {
                            item.pos = null;
                            var status = store.put(item);
                            status.onerror = function (e) {
                                console.error(e)
                            };
                            status.onsuccess = function (ev) {
                            };
                        });

                        // NOTE: need to check later! error when delete "store.delete(item)" and I think no need this
                        // _.each(items_to_delete, function (item) {
                        //     item.pos = null;
                        //     var status = store.delete(item);
                        //     status.onerror = function (e) {
                        //         console.log('>>> error when delete IndexedDB item')
                        //         console.error(e)
                        //     };
                        //     status.onsuccess = function (ev) {
                        //         console.log('>>> success when delete IndexedDB item')
                        //     };
                        // });
                    };
                });
            }

        },
        unlink: function (table_name, item) {
            console.warn('deleted id ' + item['id'] + ' of table ' + table_name);
            let sequence = Math.floor(item['id'] / 100000);
            return this.init(table_name, sequence).then(function (store) {
                try {
                    store.delete(item.id).onerror = function (e) {
                        console.error(e);
                    };
                } catch (e) {
                    console.error(e);
                }
            })
        },
        unlink_datas: function (table_name, items) {
            let sequence = 0; // only one IndexedDB
            return this.init(table_name, sequence).then(function (store) {
                _.each(items, function (item) {
                    try {
                        store.delete(item.id).onerror = function (e) {
                            console.error(e);
                        };
                    } catch (e) {
                        console.error(e);
                    }
                });
            });
        },
        unlink_data_by_ids: function (table_name, ids) {
            let sequence = 0; // only one IndexedDB
            return this.init(table_name, sequence).then(function (store) {
                _.each(ids, function (id) {
                    try {
                        store.delete(id).onerror = function (e) {
                            console.error(e);
                        };
                    } catch (e) {
                        console.error(e);
                    }
                });
            });
        },
        search_by_index: function (table_name, max_sequence, index_list, value) {
            const self = this;
            const loaded = new Promise(function (resolve, reject) {
                function load_data(sequence) {
                    self.init(table_name, sequence).then(function (object_store) {
                        for (let i = 0; i < index_list.length; i++) {
                            let index = index_list[i];
                            let idb_index = object_store.index(index);
                            let request = idb_index.get(value);
                            request.onsuccess = function (ev) {
                                var item = ev.target.result || {};
                                if (item['id']) {
                                    resolve(item)
                                }
                            };
                            request.onerror = function (error) {
                                console.error(error);
                                reject(error)
                            };
                        }
                    }, function (error) {
                        reject(error)
                    }).then(function () {
                        sequence += 1;
                        load_data(sequence);
                    });
                }

                load_data(0);
            });
            return loaded
        },
        search_read: function (table_name, sequence) {
            const self = this;
            return new Promise(function (resolve, reject) {
                self.init(table_name, sequence).then(function (store) {
                    let request = store.getAll();
                    request.onsuccess = function (ev) {
                        let items = ev.target.result || [];
                        items = items.filter(i => i.active == true);
                        resolve(items)
                    };
                    request.onerror = function (error) {
                        reject(error)
                    };
                });
            })
        },
        save_results: function (model, results) {
            if (!this.data_by_model[model]) {
                this.data_by_model[model] = results
            } else {
                this.data_by_model[model] = this.data_by_model[model].concat(results)
            }
            console.log('LOADED from indexed db with model: ' + model + ' total rows: ' + results.length)
        },
        get_data_by_id: function (table_name, keyPathID) {
            // key|keyPath|ID
            const self = this;
            let sequence = 0; // only one IndexedDB
            return new Promise(function (resolve, reject) {
                self.init(table_name, sequence).then(function (store) {
                    let request = store.get(keyPathID);
                    request.onsuccess = function (ev) {
                        let result = ev.target.result || {}; 
                        resolve(result)
                    };
                    request.onerror = function (error) {
                        console.error('[get_data_by_id] error:', error)
                        reject(false);
                    };
                });
            })
        },
        get_datas: function (model, max_sequence) {
            const self = this;
            if (model != 'cached') {
                var loaded = new Promise(function (resolve, reject) {
                    function load_data(sequence) {

                        if (sequence < max_sequence) {
                            self.search_read(model, sequence).then(function (results) {
                                if (results.length > 0) {
                                    self.save_results(model, results);
                                }
                            }).then(function () {
                                sequence += 1;
                                load_data(sequence);
                            });
                        } else {
                            resolve();
                        }
                    }

                    load_data(0);
                });
                return loaded;
            } else {
                var loaded = new Promise(function (resolve, reject) {
                    function load_data(sequence) {
                        if (sequence < max_sequence) {
                            self.search_read(model, sequence).then(function (results) {
                                resolve(results)
                            }).then(function () {
                                sequence += 1;
                                load_data(sequence);
                            });
                        } else {
                            resolve(null);
                        }
                    }

                    load_data(0);
                });
                return loaded;
            }
        },
        async auto_update_data(pos) {
            for (let model in this.data_by_model) {
                let model_object = pos.get_model(model)
                let datas = this.data_by_model[model]
                let total_rows_updated = 0
                for (let i = 0; i < datas.length; i++) {
                    let value = datas[i]
                    let results = await pos.rpc({
                        model: model,
                        method: 'search_read',
                        domain: [['id', '=', value.id]],
                        fields: model_object.fields
                    })
                    if (results.length == 1) {
                        this.write(model, results)
                    } else {
                        this.unlink(model, value)
                    }
                    total_rows_updated += 1
                    let percent_updating = (total_rows_updated / datas.length) * 100
                    pos.set('synch', {
                        status: 'connecting',
                        pending: 'Saved: ' + model + ' ' + percent_updating.toFixed(2) + ' %'
                    });
                }
            }
        }
    });

    return multi_database;
});
