odoo.define('equip3_pos_general_contd.indexedDBContd', function (require) {
    "use strict";

    var indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB || window.shimIndexedDB;
    if (!indexedDB) {
        window.alert("Your browser doesn't support a stable version of IndexedDB.")
    }
    var Backbone = window.Backbone;

    var contd_database = Backbone.Model.extend({ 
        initialize: function (session) {
            if(session){
                this.session = session;
                this.data_by_model = {}
                this.indexed_database_name = 'POS-ORDER-HISTORY_SID-' + session.config.pos_session_id + '_' + session.db
            }
        },
        init: function (table_name, sequence) {
            var self = this;
            return new Promise(function (resolve, reject) {
                const request = indexedDB.open(self.indexed_database_name, 1);
                request.onerror = function (ev) {
                    reject(ev);
                };
                request.onupgradeneeded = function (ev) {
                    var db = ev.target.result;

                    var os_order_history = db.createObjectStore('order.history', {keyPath: 'id'});
                    os_order_history.createIndex('id_index', 'id', {unique: false});

                    db.createObjectStore('cached', {keyPath: 'id'});
                };
                request.onsuccess = function (ev) {
                    var db = ev.target.result;
                    var transaction = db.transaction([table_name], 'readwrite');
                    transaction.oncomplete = function () {
                        db.close();
                    };
                    if (!transaction) {
                        reject('Cannot create transaction with: ' + table_name)
                    }
                    var store = transaction.objectStore(table_name);
                    if (!store) {
                        reject('Cannot get object store with: ' + table_name)
                    }
                    resolve(store)
                };
            })
        },
        write: function (table_name, items, cached) {
            const self = this;
            items = _.filter(items, function (item) {
                return item['active'] == true;
            });
            let last_item = items[items.length - 1];

            console.warn('[' + self.indexed_database_name + '] ' 
                + 'updating table: ' + table_name + ' log with total rows: ' 
                + items.length + ' last_item :', last_item);

            if(last_item){
                let max_id = last_item['id'];
                let sequence = 1;
                this.init(table_name, sequence).then(function (store) {
                    var request = indexedDB.open(self.indexed_database_name, 1);
                    request.onsuccess = function (ev) {
                        var db = ev.target.result;
                        var transaction = db.transaction([table_name], 'readwrite');
                        transaction.oncomplete = function () { db.close(); };
                        if (!transaction) {
                            return;
                        }
                        var store = transaction.objectStore(table_name);
                        if (!store) {
                            return;
                        }
                        _.each(items, function (item) {
                            item.pos = null;
                            item.client_use_voucher = null;
                            var status = store.put(item);
                            status.onerror = function (e) { console.error(e) };
                            status.onsuccess = function (ev) { };
                        });
                    };
                });
            }

        },
        unlink: function (table_name, item) {
            let self = this; 
            console.warn('[' + self.indexed_database_name + '] ' 
                + 'deleted id ' + item['id'] + ' of table log ' + table_name);
            let sequence = 1;
            return this.init(table_name, sequence).then(function (store) {
                try {
                    store.delete(item.id).onerror = function (e) { console.error(e); };
                } catch (e) {
                    console.error(e);
                }
            })
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
            const self = this;
            if (!self.data_by_model[model]) {
                self.data_by_model[model] = results
            } else {
                self.data_by_model[model] = self.data_by_model[model].concat(results)
            }
            console.log('[' + self.indexed_database_name + '] ' 
                + 'LOADED from indexed db with model: ' + model + ' total rows: ' + results.length)
        },
        get_datas: function (model, max_sequence) {
            const self = this;
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
        },
        fetch_datas: function (model, max_sequence) {
            const self = this;
            let datas = [];
            var loaded = new Promise(function (resolve, reject) {
                function load_data(sequence) {
                    if (sequence < max_sequence) {
                        self.search_read(model, sequence).then(function (results) {
                            if (results.length > 0) {
                                datas = datas.concat(results);
                            }
                        }).then(function () {
                            sequence += 1;
                            load_data(sequence);
                        });
                    } else {
                        resolve(datas);
                    }
                }

                load_data(0);
            });
            return loaded;
        },
        
    });

    return contd_database;
});