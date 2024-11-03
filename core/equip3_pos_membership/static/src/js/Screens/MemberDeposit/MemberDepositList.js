odoo.define('equip3_pos_membership.MemberDepositList', function (require) {
    'use strict';

    const {debounce} = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const framework = require('web.framework');
    let syncInterval = null;

    class MemberDepositList extends PosComponent {
        constructor() {
            super(...arguments); 
            this.updateDepositList = debounce(this.updateDepositList, 70);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
            this.deposits = this.env.pos.db.get_customer_deposits(); 

            this.state = {
                query: null,
                selectedDeposit: this.props.deposit,
                detailIsShown: false,
                createIsShown: false,
                isEditMode: false,
                editModeProps: {
                    deposit: null,
                },
                save_state: '',
            };
            
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('event-keyup-search-order', this._eventKeyupSearch);
            useListener('click-save', () => this.env.bus.trigger('save-deposit-member'));
            useListener('save-changes', this.saveChanges);
        }

        mounted() {
            let self = this; 
            super.mounted();
        }

        willUnmount() {
            super.willUnmount();
            clearInterval(syncInterval);
        }

        closeScreen() {
            this.trigger('close-screen');
            this.showScreen('ProductScreen');
            
            this.forceTriggerSelectedRow();
        }

        forceTriggerSelectedRow() {
            // Calling this method forcefully trigger change
            // on the selectedDeposit attribute, which then shows the screen of the
            // current deposit, essentially closing this screen.
            // this.env.pos.trigger('change:selectedDeposit', this.env.pos, this.env.pos.get_deposit());
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

        filterCheck(deposit) {
            if (this.filter && this.filter !== 'ALL') {
                const state = deposit.state;
                return this.filter === this.constants.stateSelectionFilter[state];
            }
            return true;
        }

        get getDeposits() {
            const {fieldValue, searchTerm} = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (deposit) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(deposit);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (deposit) => {
                return this.filterCheck(deposit) && searchCheck(deposit);
            };
            return this.recordList.filter(predicate);
        }

        get isNextButtonVisible() {
            return this.state.selectedDeposit ? true : false;
        }

        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.props.deposit) {
                return {command: 'set', text: 'Set Customer'};
            } else if (this.props.deposit && this.props.deposit === this.state.selectedDeposit) {
                return {command: 'deselect', text: 'Deselect Customer'};
            } else {
                return {command: 'set', text: 'Change Customer'};
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // deposit to lower its trigger rate.
        updateDepositList(event) {
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                this.state.selectedDeposit = clients[0];
                this.clickNext();
            } else {
                this.render();
            }
        }

        clickNext() {
            this.state.selectedDeposit = this.nextButton.command === 'set' ? this.state.selectedDeposit : null;
            this.confirm();
        }

        clearSearch() {
            this._initializeSearchFieldConstants();
            this.filter = this.filterOptions[0];
            this.searchDetails = {};
            this.deposits = this.env.pos.db.get_customer_deposits();
        }

        clickDeposit(event) {
            let deposit = event.detail.deposit;
            this.props.deposit = deposit;
            this.state.selectedDeposit = deposit;
            this.state.editModeProps = {
                deposit: this.state.selectedDeposit,
                selectedDeposit: this.state.selectedDeposit
            };
            this.state.detailIsShown = true;
            this.render();
        }

        async createDeposit(event) {
            this.state.createIsShown = true;
            this.render();
        }
        async discardDeposit() {
            this.state.detailIsShown = false;
            this.state.createIsShown = false;
            this.render();
        }
        get_deposit_values(vals){
            if(!vals.partner_id || !vals.payment_method_id){
                return false;
            }
            if(!vals.amount){
                return false;
            }
            if(parseInt(vals.amount) <= 0){
                return false;
            }

            vals.partner_id = parseInt(vals.partner_id);
            vals.payment_method_id = parseInt(vals.payment_method_id);
            vals.amount = parseInt(vals.amount);
            return vals;
        }

        async saveChanges(event) {
            let self = this;
            let deposit_values = this.get_deposit_values(event.detail.processedChanges);
            if (!deposit_values){
                return;
            }
            if(self.state.save_state == 'process'){
                return;
            }

            self.state.save_state = 'process';
            await self.rpc({
                model: 'customer.deposit',
                method: 'action_create_deposit_from_pos',
                args: [[], {
                    'pos_session_id': self.env.pos.pos_session.id,
                    'pos_config_id': self.env.pos.config_id,
                    'deposit_values': deposit_values,
                }],
                context: {}
            }).then(function (resp) {
                self.state.save_state = 'done';
                if(resp.status == 'success'){
                    self.showPopup('ConfirmPopup', {
                        title: 'Success',
                        body: 'Successfully create member deposit',
                        disableCancelButton: true,
                    });
                    self.discardDeposit();
                    return;
                }
                return self.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: resp.message,
                });
            });

            self.state.save_state = 'done';
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
                'ALL',
                'Draft',
                'Received',
                'Returned',
                'Converted to Revenue',
                'Reconciled',
                'Cancelled',
                'Waiting For Approval',
                'Rejected',
                'Posted',
            ];
        }

        get _stateSelectionFilter() {
            return {
                'draft': 'Draft',
                'to_approve': 'Waiting For Approval',
                'rejected': 'Rejected',
                'post': 'Received',
                'posted': 'Posted',
                'returned': 'Returned',
                'converted': 'Converted to Revenue',
                'reconciled': 'Reconciled',
                'cancelled': 'Cancelled',
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

        // TODO: save filter selected on searchbox of user for getDeposits()
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }

        // TODO: save search detail selected on searchbox of user for getDeposits()
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        
        _eventKeyupSearch(event) {
            const searchInput = event.detail
            if (searchInput != "") {
                this.deposits = this.env.pos.db.search_customer_deposits(searchInput)
            } else {
                this.deposits = this.env.pos.db.get_customer_deposits()
            } 
            this.render()
        }

        // TODO: return deposits of system
        get recordList() {
            return this.deposits;
        }
    }

    MemberDepositList.template = 'MemberDepositList';
    Registries.Component.add(MemberDepositList);
    return MemberDepositList;
});