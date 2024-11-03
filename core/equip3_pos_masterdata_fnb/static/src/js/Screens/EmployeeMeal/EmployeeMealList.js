odoo.define('equip3_pos_masterdata_fnb.EmployeeMealList', function (require) {
    'use strict';

    const {debounce} = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const framework = require('web.framework');

    class EmployeeMealList extends PosComponent {
        constructor() {
            super(...arguments); 
            this.updateEmployee = debounce(this.updateEmployee, 70);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
            this.employees = this.env.pos.db.get_employee_meal(); 

            this.state = {
                query: null,
                selectedEmployee: this.props.employee,
                selectedClient: this.props.selectedClient,
                detailIsShown: false,
                isEditMode: false,
                editModeProps: {
                    employee: null,
                    selectedClient: null
                },
            };
            
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('event-keyup-search-employee', this._eventKeyupSearchEmployee);
        }

        mounted() {
            super.mounted();
            this.getEmployeeMealsFromBackEnd();
        }

        willUnmount() {
            super.willUnmount();
        }

        async getEmployeeMealsFromBackEnd() {
            framework.blockUI()
            await this.env.pos.getEmployeeMeals();
            this.render();
            framework.unblockUI();
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

        filterCheck(employee) {
            if (this.filter && this.filter !== 'ALL') {
                const state = employee.state;
                return this.filter === this.constants.stateSelectionFilter[state];
            }
            return true;
        }

        get getEmployees() {
            const {fieldValue, searchTerm} = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (employee) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(employee);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (employee) => {
                return this.filterCheck(employee) && searchCheck(employee);
            };
            let employees = this.employeeList.filter(predicate);
            return employees
        }

        get isNextButtonVisible() {
            return this.state.selectedEmployee ? true : false;
        }

        /**
         * Returns the text and command of the next button.
         * The command field is used by the clickNext call.
         */
        get nextButton() {
            if (!this.props.employee) {
                return {command: 'set', text: 'Set Customer'};
            } else if (this.props.employee && this.props.employee === this.state.selectedEmployee) {
                return {command: 'deselect', text: 'Deselect Customer'};
            } else {
                return {command: 'set', text: 'Change Customer'};
            }
        }

        // Methods

        // We declare this event handler as a debounce function in
        // employee to lower its trigger rate.
        updateEmployee(event) {
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                this.state.selectedEmployee = clients[0];
                this.clickNext();
            } else {
                this.render();
            }
        }

        clickNext() {
            this.state.selectedEmployee = this.nextButton.command === 'set' ? this.state.selectedEmployee : null;
            this.confirm();
        }

        clearSearch() {
            this._initializeSearchFieldConstants()
            this.filter = this.filterOptions[0];
            this.searchDetails = {};
            this.employees = this.env.pos.db.get_employee_meal()
            this.getEmployeeMealsFromBackEnd()
        }

        clickEmployee(event) {
            let employee = event.detail.employee;
            let order = this.env.pos.get_order(); 

            order.employeemeal_employee_id = employee.id;
            order.employeemeal_employee_name = employee.name;
            order.employeemeal_budget = employee.remaining_budget;

            this.trigger('close-temp-screen');
            this.updateSummary();
        }

        updateSummary(){
            let order = this.env.pos.get_order(); 
            var currency = false
            if(order){
                currency = order.currency
            }
            let limit_budget = this.env.pos.config.employee_meal_limit_budget;

            let $employee_name = $('.summary-employee-budget-line .employee_name');
            $employee_name.text('');
            if(typeof order.employeemeal_budget != 'undefined'){
                limit_budget =  order.employeemeal_budget;
                $employee_name.text(' (' + order.employeemeal_employee_name + ')');
            }
            $('.summary-employee-budget').text(this.env.pos.format_currency(limit_budget,false,currency))
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
            return {}
        }

        // TODO: define group filters
        get filterOptions() { // list state for filter
            return [ 'ALL', ];
        }

        get _stateSelectionFilter() {
            return {
                // 'new' : 'New',
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

        // TODO: save filter selected on searchbox of user for getEmployeeMeals()
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }

        // TODO: save search detail selected on searchbox of user for getEmployeeMeals()
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        
        _eventKeyupSearchEmployee(event) {
            const searchInput = event.detail
            if (searchInput != "") {
                this.employees = this.env.pos.db.search_employee_meal(searchInput);
            } else {
                this.employees = this.env.pos.db.get_employee_meal();
            } 
            this.render()
        }

        // TODO: return employees of system
        get employeeList() {
            let employees = this.employees.filter((e) => {
                if(e.remaining_budget > 0){
                    return true;
                }
                return false;
            });
            return employees;
        }
    }

    EmployeeMealList.template = 'EmployeeMealList';
    Registries.Component.add(EmployeeMealList);
    return EmployeeMealList;
});