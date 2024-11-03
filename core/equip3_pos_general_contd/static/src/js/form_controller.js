odoo.define('equip3_pos_general_contd.PosGeneralContdFormController', function(require) {
    "use strict";

    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var _t = core._t;
    var PosGeneralFormController = require('equip3_pos_general.PosGeneralFormController');

    let PosGeneralContdFormController = FormController.include({

        // TODO: Download paid pos session order (complete order) when left unsynced
        _actionPosDownloadPaidOrders: function (session) {
            this._actionPosDownloadOrderHistoryLocal(session);
            this._super.apply(this, arguments);
        },

        // TODO: Backup session order stored in the indexedDB
        _actionPosDownloadOrderHistoryLocal: function (session) {
            let self = this;
            if(session.is_pos_config_save_order_history_local){
                console.warn('[_actionPosDownloadOrderHistoryLocal] backup local order log from indexedDB');
                var indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB || window.shimIndexedDB;
                if (!indexedDB) {
                    window.alert("Your browser doesn't support a stable version of IndexedDB.");
                    return;
                } else {
                    let indexed_database_name = 'POS-ORDER-HISTORY_SID-' + session.id + '_' + odoo.session_info.db;
                    let request = indexedDB.open(indexed_database_name, 1);
                    request.onsuccess = function (ev) {
                        let db = ev.target.result;
                        let table_name = 'order.history';
                        let transaction = null;
                        try {
                            transaction = db.transaction([table_name], "readwrite");
                        } catch (err) {
                            console.error('[_actionPosDownloadOrderHistoryLocal] transaction error:', err.message)
                        }
                        if (!transaction) {
                            console.error('[_actionPosDownloadOrderHistoryLocal] Cannot create transaction with ' + table_name);
                            return;
                        }
                        transaction.oncomplete = function () {
                            db.close();
                        };
                        let store = transaction.objectStore(table_name);
                        if (!store) {
                            console.error('[_actionPosDownloadOrderHistoryLocal] Cannot get object store with ' + table_name);
                            return;
                        }

                        let request = store.getAll();
                        request.onsuccess = function (ev) {
                            let result = ev.target.result || []; 
                            console.warn('Result:', result);
                            let filename = `backup_local_order_log_${moment().format('YYYY-MM-DD-HH-mm-ss')}.json`;
                            self._actionPosDownloadData(filename, JSON.stringify(result));
                        };
                        request.onerror = function (error) {
                            console.error('[_actionPosDownloadOrderHistoryLocal] error:', error)
                        };
                    };
                }
            }
        },

    });

    return PosGeneralContdFormController;
});