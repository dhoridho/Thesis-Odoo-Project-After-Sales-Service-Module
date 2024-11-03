odoo.define('equip3_pos_masterdata.PosOrderScreen', function (require) {
    'use strict';

    const {debounce} = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const framework = require('web.framework');

    /**
     * @props order - originally selected order
     */
    class PosOrderScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click-view', () => this.viewOrder());
            this.state = {
                query: null,
                selectedOrder: this.props.order,
                selectedClient: this.props.selectedClient,
                detailIsShown: false,
                isEditMode: false,
                editModeProps: {
                    order: null,
                    selectedClient: null,
                },
            };
            if (this.props.order) {
                this.state.detailIsShown = true
                this.state.editModeProps = {
                    order: this.props.order,
                };
            }
            this.props.page_pagination = 1
            this.props.max_line_perpage = 10
            this.props.max_pagination_button = 7
            this.props.group_pagination_button = 1

            this.updateOrderList = debounce(this.updateOrderList, 70);
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('event-keyup-search-order', this._eventKeyupSearchOrder);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
            var domain_state_not_include = ['cancel']
            if(this.env.pos.config.order_loading_options=='n_days'){
                var today = new Date();
                var validation_date = new Date(today.setDate(today.getDate()-this.env.pos.config.number_of_days));
                this.order_history = this.env.pos.db.pos_orders.filter((o) => new Date(o.date_order) >= validation_date && !domain_state_not_include.includes(o.state) && o.config_id[0]==this.env.pos.config.id)
            }
            else if(this.env.pos.config.order_loading_options == 'current_session') {
                var session_active_ids = []
                var session_active = this.env.pos.pos_sessions.filter((o) => o.config_id[0]==this.env.pos.config.id && ['opened','opening_control'].includes(o.state))
                for(var ii = 0, len = session_active.length; ii < len; ii++){
                    session_active_ids.push(session_active[ii].id)
                }
                this.order_history = this.env.pos.db.pos_orders.filter((a) => session_active_ids.includes(a.session_id[0])  && !domain_state_not_include.includes(a.state) )
            }
            else{
                this.order_history = this.env.pos.db.pos_orders.filter((o) => !domain_state_not_include.includes(o.state) && o.config_id[0]==this.env.pos.config.id)
            }
            this.orders = this.order_history
        }

        mounted() {
            super.mounted()
        }

        willUnmount() {
            super.willUnmount()
        }

        reset_pagination(){
            this.props.page_pagination = 1
            this.props.group_pagination_button = 1
        }

        back() {
            if (this.state.detailIsShown) {
                this.state.detailIsShown = false;
                this.render();
            } else {
                this.props.resolve({confirmed: false, payload: false});
                this.trigger('close-temp-screen');
            }
        }

        closeScreen() {
            this.trigger('close-temp-screen');
            this.forceTriggerSelectedOrder();
        }
        
        forceTriggerSelectedOrder() { 
            let currentOrder = this.env.pos.get_order();
            if(currentOrder){
                if(currentOrder.is_complete){
                    currentOrder.finalize();
                }
            }

            // Calling this method forcefully trigger change
            // on the selectedOrder attribute, which then shows the screen of the
            // current order, essentially closing this screen.
            this.env.pos.trigger('change:selectedOrder', this.env.pos, this.env.pos.get_order());
        }

        confirm() {
            this.props.resolve({confirmed: true, payload: this.state.selectedOrder});
            this.trigger('close-temp-screen');
        }

        get currentOrder() {
            return this.env.pos.get_order();
        }

        get getOrders() {
            const filterCheck = (order) => {
                if (this.filter && this.filter !== 'All Items') {
                    const state = order.state;
                    return this.filter === this.constants.stateSelectionFilter[state];
                }
                return true;
            };
            const {fieldValue, searchTerm} = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (order) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return filterCheck(order) && searchCheck(order);
            };
            let orders = this.orderList.filter(predicate);
            orders = orders.filter((o) => !o.so_pickup_id )
            let client = this.state.selectedClient;
            if (client) {
                orders = orders.filter((o) => o.partner_id && o.partner_id[0] == client.id)
                return orders
            } else {
                return orders
            }
        }

        get getOrdersPagination() {
            var res = this.getOrders
            var min = 0
            if(this.props.page_pagination > 1){
                min += (this.props.page_pagination-1)* this.props.max_line_perpage 
            }
            var max = min+this.props.max_line_perpage
            return res.slice(min, max)
        }

        get lengthPagination(){
            var length_order = this.getOrders.length
            var max_line_perpage = this.props.max_line_perpage
            var length_record = Math.ceil(length_order / max_line_perpage);
            var count = 0
            var res = []
            var count = 0
            var first_pagination = this.props.group_pagination_button 
            if (first_pagination>1)
            {
                first_pagination = ((this.props.group_pagination_button  - 1) * this.props.max_pagination_button) + 1
            }
            for(var ii = first_pagination ; ii <= length_record; ii++){
                res.push(ii)
                count+=1
                if (count==this.props.max_pagination_button){
                    break
                }
            }
            return res
        }

        get IsSHowPrevPagination(){
            if(1!=this.props.page_pagination){
                return true
            }
            else{
                return false
            }

        }

        get IsSHowNextPagination(){
            var length_order = this.getOrders.length
            var max_line_perpage = this.props.max_line_perpage
            var length_record = Math.ceil(length_order / max_line_perpage);
            if(this.props.page_pagination!=length_record){
                return true
            }
            else{
                return false
            }
        }

        clickNextPagination(){
            var length_order = this.getOrders.length
            var max_line_perpage = this.props.max_line_perpage
            var length_record = Math.ceil(length_order / max_line_perpage);
            var pagination = this.lengthPagination
            if(pagination[pagination.length-1]==this.props.page_pagination){
                this.props.group_pagination_button+=1
                this.SetPaginationAuto()
            }
            else{
                this.props.page_pagination+=1
                this.render()
            }
            
            
            
        }
        clickPrevPagination(){
            var length_order = this.getOrders.length
            var max_line_perpage = this.props.max_line_perpage
            var length_record = Math.ceil(length_order / max_line_perpage);
            var pagination = this.lengthPagination
            if(pagination[0]==this.props.page_pagination){
                this.props.group_pagination_button-=1
                this.SetPaginationAuto()
                var last_pagination = this.lengthPagination[this.lengthPagination.length-1]
                this.clickPagination(last_pagination)
            }
            else{
                this.props.page_pagination-=1
                this.render()
            }
        }


        SetPaginationAuto(){
            var length_order = this.getOrders.length
            var max_line_perpage = this.props.max_line_perpage
            var length_record = Math.ceil(length_order / max_line_perpage);
            var pagination = this.lengthPagination
            var first_pagination = pagination[0]
            this.clickPagination(first_pagination)
        }


        get isNextButtonVisible() {
            return this.state.selectedOrder ? true : false;
        }

        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.props.order) {
                return {command: 'set', text: 'Set Customer'};
            } else if (this.props.order && this.props.order === this.state.selectedOrder) {
                return {command: 'deselect', text: 'Deselect Customer'};
            } else {
                return {command: 'set', text: 'Change Customer'};
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // order to lower its trigger rate.
        updateOrderList(event) {
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                this.state.selectedOrder = clients[0];
                this.clickNext();
            } else {
                this.render();
            }
        }
        clickPagination(Pagination){
            this.props.page_pagination = parseInt(Pagination)
            this.render()
        }
        clickOrder(event) {
            let orderId = event.detail.id;
            let orderSelected = this.env.pos.db.order_by_id[orderId]
            this.state.selectedOrder = orderSelected;
            this.state.editModeProps = {
                order: this.state.selectedOrder,
                selectedOrder: this.state.selectedOrder
            };
            this.state.detailIsShown = true;
            this.render();
        }

        viewOrder() {
            this.state.editModeProps = {
                order: this.state.selectedOrder,
            };
            this.render();
        }

        clickNext() {
            this.state.selectedOrder = this.nextButton.command === 'set' ? this.state.selectedOrder : null;
            this.confirm();
        }

        activateEditMode(event) {
            const {isNewClient} = event.detail;
            this.state.isEditMode = true;
            this.state.detailIsShown = true;
            this.state.isNewClient = isNewClient;
            if (!isNewClient) {
                this.state.editModeProps = {
                    partner: this.state.selectedOrder,
                };
            }
            this.render();
        }

        deactivateEditMode() {
            this.state.isEditMode = false;
            this.state.editModeProps = {
                partner: {
                    country_id: this.env.pos.company.country_id,
                    state_id: this.env.pos.company.state_id,
                },
            };
            this.render();
        }

        cancelEdit() {
            this.deactivateEditMode();
        }

        clearSearch() {
            this.reset_pagination()
            this._initializeSearchFieldConstants()
            this.filter = this.filterOptions[0];
            this.searchDetails = {};
            this.state.editModeProps = {
                order: null,
                selectedClient: null
            };
            this.state.selectedClient = null
            this.state.selectedOrder = null
            this.orders = this.env.pos.db.pos_orders 
            this.render()
        }


        // TODO: ==================== Seach bar example ====================

        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: {show: true, options: this.filterOptions},
            };
        }

        // TODO: define search fields
        get _searchFields() {
            return {} // TODO: 15.07.2021 turnoff it, automatic search when cashier typing searchbox
            // var fields = {
            //     'Order Receipt': (order) => order.name,
            //     'Receipt Number': (order) => order.pos_reference,
            //     'Sale Person': (order) => order.sale_person,
            //     'Create Date (MM/DD/YYYY)': (order) => moment(order.create_date).format('MM/DD/YYYY hh:mm A'),
            //     'Order Date (MM/DD/YYYY)': (order) => moment(order.date_order).format('MM/DD/YYYY hh:mm A'),
            //     'Paid Date (MM/DD/YYYY)': (order) => moment(order.paid_date).format('MM/DD/YYYY hh:mm A'),
            //     Customer: (order) => order.partner_id[1],
            //     Session: (order) => order.session,
            //     Ean13: (order) => order.ean13,
            //     ID: (order) => order.id,
            // };
            // return fields;
        }

        // TODO: define group filters
        get filterOptions() { // list state for filter
            return [
                'All Items',
                'Not Full Fill Payment',
                'Cancelled',
                'Partially Paid',
                'Paid',
                'Done',
                'Invoiced',
                'Quotation',
                'Delivery',
                'Delivered',
                'Received',
            ];
        }

        get _stateSelectionFilter() {
            return {
                'draft': 'Not Full Fill Payment',
                'cancel': 'Cancelled',
                'paid': 'Paid',
                'done': 'Done',
                'invoiced': 'Invoiced',
                'quotation': 'Quotation',
                'delivery': 'Delivery',
                'delivered': 'Delivered',
                'partially paid': 'Partially Paid',
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

        // TODO: save filter selected on searchbox of user for getOrders()
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.reset_pagination()
            this.render();
        }

        // TODO: save search detail selected on searchbox of user for getOrders()
        async _onSearch(event) {
            let order_object = this.env.pos.get_model('pos.order');
            var self = this
            const searchDetails = event.detail;
            //TODO : SCAN BARCODE EAN13
            if(searchDetails) {
                if(searchDetails.searchTerm.length > 6){
                    var order_ean13 = this.env.pos.db.pos_orders.filter((o) => o.ean13==searchDetails.searchTerm)
                    if(order_ean13.length > 0) {
                        this.orders = order_ean13
                        event.detail.id = order_ean13[0].id
                        this.clickOrder(event)
                    }
                }
            }
            Object.assign(this.searchDetails, searchDetails);
            this.reset_pagination()
            this.render();
        }

        _eventKeyupSearchOrder(event) {
            const searchInput = event.detail
            if (searchInput != "") {
                this.orders = this.env.pos.db.search_order(searchInput)
            } else {
                this.orders = this.order_history
            }
            this.reset_pagination()
            this.render()

        }

        // TODO: return orders of system
        get orderList() {
            let self = this;
            let orders = this.orders;

            if(self.props.outstanding_receivable){
                orders = orders.filter((o) => {
                    if(o.partner && o.partner.id == self.props.filteredPartnerId && ['invoiced','partially paid'].includes(o.state)){
                        return true
                    }
                    return false;
                });
            }

            const formatDate = (str) => {
                const [_, yyyy, mm, dd, hh, min, ss] = str.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
                return new Date(yyyy, mm-1, dd, hh, min, min);
            };
            orders = orders.sort((a, b) => formatDate(b.date_order) - formatDate(a.date_order)); // Sort Order by date DESC

            return orders;
        }
    }

    PosOrderScreen.template = 'PosOrderScreen';

    Registries.Component.add(PosOrderScreen);

    return PosOrderScreen;
});
