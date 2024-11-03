var employee_data = [];
var emp_form_id;
var parent_id;
var direction;
var verticalLevel;
var oc;
var isPermitted = false;

odoo.define("org_chart_premium.org_chart", function (require) {
  "use strict";

  var core = require('web.core');
  var session = require('web.session');
  var ajax = require('web.ajax');
  var AbstractAction = require('web.AbstractAction');
  var Widget = require('web.Widget');
  // var ControlPanelMixin = require('web.ControlPanelMixin');
  var Dialog = require('web.Dialog');
  var QWeb = core.qweb;
  var _t = core._t;
  var _lt = core._lt;

  var OrgChartEmployee = AbstractAction.extend({
    events: _.extend({}, Widget.prototype.events, {
          'click #btn-reload': 'reload_org_chart',
          'click #btn-export': 'export_org_chart',
          'click .add_node': 'add_noeud',
          'click .edit_node': 'edit_noeud',
          'click .delete_node': 'delete_noeud',
          'click #btn-switch': 'switch_org_chart',
          'drop .node': 'action_drop',
          'click .btn-sort': 'sort_filter_data',
  	}),
    init: function(parent, context) {
      this._super(parent, context);
        var self = this;
        if (context.tag == 'org_chart_premium.org_chart_employee') {
            // Get Form_id and Defaults Direction and verticalLevel
            self._rpc({
                model: 'org.chart.employee',
                method: 'get_emp_form_id',
            }, []).then(function(result){
                emp_form_id = result.form_id;
                direction = result.direction;
                verticalLevel = result.vertical_level;
                self.verticalLevel = verticalLevel;
            }).then(function (){
              self.show_org_chart();
            });
            
            // check current user group
            session.user_has_group('equip3_hr_employee_access_right_setting.group_hr_manager').then(function(has_group) {
              if(has_group) {
                isPermitted = true
              }
            });
        }
    },
    willStart: function() {
      return $.when(ajax.loadLibs(this), this._super());
    },
    start: function() {
      var self = this;
      return this._super();
    },
    render: function() {
        var super_render = this._super;
        var self = this;
        var org_chart = QWeb.render('org_chart_premium.org_chart_template', {
            widget: self,
        });
        $( ".o_control_panel" ).addClass( "o_hidden" );
        $(org_chart).prependTo(self.$el);
        return org_chart;
    },
    reload: function () {
      window.location.href = this.href;
    },
    reload_org_chart: function(event) {
      $("#org-chart-main").remove();
      // $("#chart-container").remove();
      // $("#btn-reload").remove();
      // $("#btn-export").remove();
      // $("#key-word").remove();
      // $("#btn-switch").remove();
      this.show_org_chart();
    },
    switch_org_chart: function(event) {
      direction = get_direction(direction);
      this.reload_org_chart();
    },
    show_org_chart: function (event) {
      var self = this;
      self._rpc({
          model: 'org.chart.employee',
          method: 'get_employee_data',
      }, []).then(function(result){
          employee_data = result;
      }).then(function(){
          self.render();
          self.href = window.location.href;
      }).then(function() {
        oc = get_organization_chart(employee_data.values, direction, verticalLevel, isPermitted);
        oc.$chart.on('nodedrop.orgchart', function(event, extraParams) {
          var data = {
            "child": extraParams.draggedNode.children('.org_chart_id').text(),
            "last_parent": extraParams.dragZone.children('.org_chart_id').text(),
            "new_parent": extraParams.dropZone.children('.org_chart_id').text()
          };
          parent_id = extraParams.draggedNode.children('.org_chart_id').text();
          $.ajax({
            type: "POST",
            dataType: "json",
            url: "/orgchart/update",
            data: data,
          });
        });
      }).then(function () {
        $('.o_content').addClass('o_hidden');
        if (direction != undefined && direction != 'l2r') {
          $('#org-chart-main').addClass('org-chart-scroll');
        }
      });
    },
    export_org_chart: function (event) {
      $('.third-menu-icon').addClass('o_hidden');
      $('#org-chart-main').removeClass('org-chart-scroll');
      $('#chart-container').addClass('org-chart-scroll');
      $('.orgchart').removeClass('orgchartwindowsize');
      var that = oc;
      that.export(that.options.exportFilename, that.options.exportFileextension);
      $('.third-menu-icon').removeClass('o_hidden');
      if (direction == 'l2r') {
        $('#org-chart-main').addClass('org-chart-scroll');
      }
      $('#chart-container').removeClass('org-chart-scroll');
      $('.orgchart').removeClass('orgchartwindowsize');
    },
    add_noeud: function (event){
      var self = this;
      event.stopPropagation();
      event.preventDefault();
      self.do_action({
          name: _t("Add new Employee"),
          type: 'ir.actions.act_window',
          res_model: 'hr.employee',
          view_mode: 'form',
          view_type: 'form',
          context: {'parent_id': parseInt(event.target.id)},
          views: [[emp_form_id, 'form']],
          target: 'new'
      },{on_reverse_breadcrumb: function(){ return self.reload();}})
    },
    edit_noeud: function (event){
      var self = this;
      event.stopPropagation();
      event.preventDefault();
      self.do_action({
          name: _t("Edit Employee"),
          type: 'ir.actions.act_window',
          res_model: 'hr.employee',
          view_mode: 'form',
          view_type: 'form',
          res_id: parseInt(event.target.id),
          views: [[emp_form_id, 'form']],
          target: 'new'
      },{on_reverse_breadcrumb: function(){ return self.reload();}})
    },
    delete_noeud: function (event){
      var self = this;
      var options = {
        confirm_callback: function () {
          self._rpc({
              model: 'hr.employee',
              method: 'unlink',
              args: [parseInt(event.target.id)],
          }, [])
          .then(function(){
            location.reload();
          });
        }
      };
      Dialog.confirm(this, _t("Do you Want to Delete this Employee ?"), options);
    },
    action_drop: function (event){
      var self = this;
      self._rpc({
          route: "/orgchart/ondrop",
          params: {
              employee_id: parseInt(parent_id),
          },
      })
      .then(function (result) {
          self.do_action(result);
      });
    },
    sort_filter_data: function(event) {
      var sort = '';
      if ($(event.currentTarget).hasClass('fa-caret-down')) {
        sort = 'desc'
      } else {
        sort = 'asc'
      }
      if (event.currentTarget.id == 'job-sort') {
        this.filterByJobPosition(undefined, sort);
      } else if (event.currentTarget.id == 'dept-sort') {
        this.filterByDepartment(undefined, sort);
      }
    },
  });

  core.action_registry.add('org_chart_premium.org_chart_employee', OrgChartEmployee);

  return OrgChartEmployee;

});
