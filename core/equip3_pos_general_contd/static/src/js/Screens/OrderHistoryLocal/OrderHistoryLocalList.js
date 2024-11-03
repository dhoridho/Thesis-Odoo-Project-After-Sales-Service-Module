odoo.define('equip3_pos_general_contd.OrderHistoryLocalList', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const framework = require('web.framework');
    const Session = require('web.Session');
    const {Gui} = require('point_of_sale.Gui');
    const {useListener} = require('web.custom_hooks');
    const {debounce} = owl.utils;
    const { useState } = owl.hooks;



    class OrderHistoryLocalList extends PosComponent {
        constructor() {
            super(...arguments); 
            this.updateRecordList = debounce(this.updateRecordList, 70);
            this.searchDetails = {};
            this.filter = 'Not Sync';
            this._initializeSearchFieldConstants();
            this.records = this.env.pos.db.get_order_history_local(); 

            this.state = useState({
                query: null,
                selectedRecord: this.props.record,
                detailIsShown: false,
                createIsShown: false,
                isEditMode: false,
                editModeProps: {
                    record: null,
                },
                save_state: '',
                action: {
                    label: this.env._t('Action'),
                    showOptions: false,
                    options: ['Export', 'Import'],
                },
            });
            this.sync = useState({ 'state': '' , 'order': {} });
            
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('event-keyup-search-order', this._eventKeyupSearch);
        }

        mounted() {
            let self = this; 
            super.mounted();
        }

        willUnmount() {
            super.willUnmount();
        }

        closeScreen() {
            this.trigger('close-screen');
            this.showScreen('ProductScreen');
            this.forceTriggerSelectedRow();
        }

        forceTriggerSelectedRow() {
            // Calling this method forcefully trigger change
            // on the selectedRecord attribute, which then shows the screen of the
            // current record, essentially closing this screen.
            // this.env.pos.trigger('change:selectedRecord', this.env.pos, this.env.pos.get_deposit());
        }

        async back() {
            if (this.state.detailIsShown) {
                this.state.detailIsShown = false;
                this.render();
            } else {
                this.props.resolve({confirmed: false, payload: false});
                this.trigger('close-temp-screen');
            }
        }

        filterCheck(record) {
            if (this.filter && this.filter !== 'ALL') {
                const state = record.sync_state; // filter by sync state
                return this.filter === this.constants.stateSelectionFilter[state];
            }
            return true;
        }

        get getRecords() {
            const {fieldValue, searchTerm} = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (record) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(record);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (record) => {
                return this.filterCheck(record) && searchCheck(record);
            };
            return this.recordList.filter(predicate);
        }

        get isNextButtonVisible() {
            return this.state.selectedRecord ? true : false;
        }

        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.props.record) {
                return {command: 'set', text: 'Set Customer'};
            } else if (this.props.record && this.props.record === this.state.selectedRecord) {
                return {command: 'deselect', text: 'Deselect Customer'};
            } else {
                return {command: 'set', text: 'Change Customer'};
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // record to lower its trigger rate.
        updateRecordList(event) {
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                this.state.selectedRecord = clients[0];
                this.clickNext();
            } else {
                this.render();
            }
        }

        clickNext() {
            this.state.selectedRecord = this.nextButton.command === 'set' ? this.state.selectedRecord : null;
            this.confirm();
        }

        async pushOrders() {
            let self = this;
            if (self.sync.state == 'connecting') {
                return false;
            }

            const pingServer = await self.env.pos._check_connection();
            if (!pingServer) {
                this.env.pos.alert_message({
                    title: this.env._t('Offline'),
                    body: this.env._t('Your Internet or Hashmicro Server Offline')
                })
                return false;
            }

            let records = this.env.pos.db.get_order_history_local();
            let not_sync_records = records.filter((o)=>!o.sync_state || (o.sync_state && o.sync_state == 'Not Sync'));
            let order_uids = not_sync_records.map(o=>o.name);

            self.sync.state = 'connecting';
            let result = await self.rpc({
                model: 'pos.order',
                method: 'check_sync_order',
                args: [[], { 'order_uids': order_uids }]
            }, {
                shadow: true,
                timeout: 5000 // 5 seconds
            }).then(function (response) {
                return response;
            }).guardedCatch(function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[pushOrder] ~ Server Offline:', error)
                    self.env.pos.alert_message({
                        title: self.env._t('Offline'),
                        body: self.env._t('Your Internet or Hashmicro Server Offline.')
                    });
                } else {
                    error.event.preventDefault(); // Stop default popup error
                    console.error('[pushOrder] ~ Error 403', error);
                    Gui.showPopup('PosErrorMessagePopup', {
                        title: self.env._t('Failed Sync Orders'),
                        message: error.message,
                    })
                }
                self.sync.state = 'error';
                return null;
            });
            console.warn('[pushOrder] ~ result:', result);

            if (result) {
                for (let pos_reference of result.sync_order_uids){
                    let order_log = self.env.pos.db.get_order_history_local_by_name(pos_reference);
                    if (order_log) {
                        order_log.sync_state = 'Synced';
                        self.env.pos.update_order_history_local(order_log); // save to IndexedDB
                        self.env.pos.db.save_order_history_local([order_log]); // update variables
                    }
                }
                for (let pos_reference of result.notsync_order_uids){
                    let order_log = self.env.pos.db.get_order_history_local_by_name(pos_reference);
                    if (order_log){
                        let data_orders = [self.env.pos._prepare_data_from_local_order_log(JSON.parse(JSON.stringify(order_log)))];
                        let push_order_one = await self.env.pos._force_push_orders(data_orders, { show_error: true }); 
                        if(push_order_one.length){
                            order_log = JSON.parse(JSON.stringify(order_log));
                            order_log.sync_state = 'Synced';
                            self.env.pos.update_order_history_local(order_log); // save to IndexedDB
                            self.env.pos.db.save_order_history_local([order_log]); // update variables
                        }
                    }
                }
                self.sync.state = 'done';
            }
        }

        clearSearch() {
            this._initializeSearchFieldConstants();
            this.searchDetails = {};
            this.records = this.env.pos.db.get_order_history_local();
            this.render();
        }

        refreshScreen() {
            this._initializeSearchFieldConstants();
            this.records = this.env.pos.db.get_order_history_local();
            this.render();
        }

        clickRecord(record) {
            this.props.record = record;
            this.state.selectedRecord = record;
            this.state.editModeProps = {
                record: this.state.selectedRecord,
                selectedRecord: this.state.selectedRecord
            };
            this.state.detailIsShown = true;
            this.render();
        }

        // TODO: ==================== Search bar example ====================
        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: {show: true, options: this.filterOptions},
            };
        }

        // TODO: define search fields
        get _searchFields() {
            return {} // TODO: 15.07.2021 turnoff it, automatic search when cashier typing searchbox
        }

        // TODO: define group filters
        get filterOptions() { // list state for filter
            return [
                'Not Sync',
                'Synced',
            ];
        }

        get _stateSelectionFilter() {
            return {
                'Not Sync': 'Not Sync',
                'Synced': 'Synced',
            };
        }

        // TODO: register search bar
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
                stateSelectionFilter: this._stateSelectionFilter,
            });
        }

        // TODO: save filter selected on searchbox of user for getRecords()
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }

        // TODO: save search detail selected on searchbox of user for getRecords()
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        
        _eventKeyupSearch(event) {
            const searchInput = event.detail
            if (searchInput != "") {
                this.records = this.env.pos.db.search_order_history_local(searchInput);
            } else {
                this.records = this.env.pos.db.get_order_history_local();
            } 
            this.render()
        }

        async selectAction(option){
            if(option == 'Import'){
                this._actionImport();
            }
            if(option == 'Export'){
                this._actionExport();
            }
        }

        async _actionImport(){
            let self = this
            let {confirmed, payload: payload} = await Gui.showPopup('ImportFilePopup', {title: this.env._t('Import'), });
            if(confirmed){
                let orders = JSON.parse(payload.data);
                console.warn('[_actionImport] orders:', orders)
                if(orders.length){
                    for (var i = orders.length - 1; i >= 0; i--) {
                        orders[i].is_from_import = true;
                    }
                    self.env.pos.indexedDBContd.write('order.history', orders);
                    self.env.pos.db.save_order_history_local(orders);
                    self.refreshScreen();
                }
            }
        }

        async _actionExport(){
            let export_data = this.getRecords;
            console.warn('[_actionExport] export_data:', export_data)
            let filename = `local_order_log_${moment().format('YYYY-MM-DD-HH-mm-ss')}.json`;
            await this.download(filename, JSON.stringify(export_data));
        }

        async download(filename, text) {
            this.env.pos.alert_message({
                title: this.env._t('Warning'),
                body: this.env._t('Preparing download file, please wait for moment.')
            });

            const blob = new Blob([text]);
            const URL = window.URL || window.webkitURL;
            const url =  URL.createObjectURL(blob);
            const element = document.createElement('a');
            element.setAttribute('href', url);
            element.setAttribute('download', filename);
            element.style.display = 'none';
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
        }

        // TODO: return records of system
        get recordList() {
            return this.records;
        }

        getRecordCount(){
            return this.records.length;
        }

    }

    OrderHistoryLocalList.template = 'OrderHistoryLocalList';
    Registries.Component.add(OrderHistoryLocalList);
    return OrderHistoryLocalList;
});