var department_data = [];
var parent_id;
var direction;
var verticalLevel;
var oc;
var job_id;

var nodeTemplateDept = function(data) {
    var titleValue = data.title
    if (data.className == 'job-level' && data.title == '0') {
      titleValue = ''
    }
    return `
        <div class="title" title="${data.name}">${data.name}</div>
        <div class="content">${titleValue}</div>
        <div class="employee-data" style="display:none; color:white; text-align:left; padding-left:10%; ">${data.employeeData}</div>
    `;
};

function get_organization_dept_chart(datascource, direction, verticalLevel) {
  var oc = $('#chart-container').orgchart({
    'data' : datascource,
    'nodeTemplate': nodeTemplateDept,
    'toggleSiblingsResp': true,
    'draggable': false,
    'exportFilename': 'OrgChartDepartmentPro',
    'verticalLevel': verticalLevel,
    'direction': direction,
    'dropCriteria': function($draggedNode, $dragZone, $dropZone) {
      if($draggedNode.find('.content').text().indexOf('manager') > -1 && $dropZone.find('.content').text().indexOf('engineer') > -1) {
        return false;
      }
      return true;
    },
  });
  return oc;
}

function get_direction(current_direction) {
  if (current_direction == 'l2r'){
    return false;
  }
  return 'l2r';
}

$(document).on('click', '.job-id', function(event) {
  job_id = this.getAttribute('data-id');
});

// Get the type of exported file
function exportForm() {
  var self = this;
  var exportFileExtension = self.$('select[name="output_type"]').val();
  var that = oc;

  $('.third-menu-icon').addClass('o_hidden');
  $('#org-chart-main').removeClass('org-chart-scroll');
  $('#chart-container').addClass('org-chart-scroll');
  $('.orgchart').removeClass('orgchartwindowsize');

  that.options.exportFileextension = JSON.parse(exportFileExtension);
  that.export(that.options.exportFilename, that.options.exportFileextension);

  $('.third-menu-icon').removeClass('o_hidden');
  if (direction == 'l2r') {
    $('#org-chart-main').addClass('org-chart-scroll');
  }
  
  $('#chart-container').removeClass('org-chart-scroll');
  $('.orgchart').removeClass('orgchartwindowsize');
}

odoo.define("equip3_hr_masterdata_employee.org_chart", function (require) {
  "use strict";

  var core = require('web.core');
  var session = require('web.session');
  var ajax = require('web.ajax');
  var AbstractAction = require('web.AbstractAction');
  var Widget = require('web.Widget');
  var QWeb = core.qweb;
  var _t = core._t;

  var OrgChartDepartment = AbstractAction.extend({
    events: _.extend({}, Widget.prototype.events, {
        'click #btn-reload': 'reload_org_chart',
        'click .fa-users': 'open_employee_data',
        'click #btn-switch': 'switch_org_chart',
        'click #btn-export': 'export_org_chart',
        'click #search-job-position': 'click_search_job_position',
        'click #search-dept': 'click_search_dept',
        'click .btn-sort': 'sort_filter_data',
  	}),

    init: function(parent, context) {
        this._super(parent, context);
        var self = this;
        if (context.tag == 'equip3_hr_masterdata_employee.org_chart_department') {
            self.show_org_chart();
        }
    },

    createNode: function (data) {
      var that = this;
      var opts = this.options;
      var level = data.level;
      if (data.children) {
        $.each(data.children, function (index, child) {
          child.parentId = data.id;
        });
      }
      // construct the content of node
      var $nodeDiv = $('<div' + (opts.draggable ? ' draggable="false"' : '') + (data[opts.nodeId] ? ' id="' + data[opts.nodeId] + '"' : '') + (data.parentId ? ' data-parent="' + data.parentId + '"' : '') + '>')
        .addClass('node ' + (data.className || '') +  (level > opts.visibleLevel ? ' slide-up' : ''));
      if (opts.nodeTemplate) {
        $nodeDiv.append(opts.nodeTemplate(data));
        $nodeDiv.append('<div class="org_chart_id">' + data['id'] + '</div>');
      } else {
        $nodeDiv.append('<div class="title">' + data[opts.nodeTitle] + '</div>')
          .append(typeof opts.nodeContent !== 'undefined' ? '<div class="content">' + (data[opts.nodeContent] || '') + '</div>' : '');
        // Add id
        $nodeDiv.append('<div class="org_chart_id">' + data['id'] + '</div>');
      }
      //
      var nodeData = $.extend({}, data);
      delete nodeData.children;
      $nodeDiv.data('nodeData', nodeData);
      // append 4 direction arrows or expand/collapse buttons
      var flags = data.relationship || '';
      if (opts.verticalLevel && level >= opts.verticalLevel) {
        if ((level + 1) > opts.verticalLevel && Number(flags.substr(2,1))) {
          var icon = level + 1 > opts.visibleLevel ? 'plus' : 'minus';
          $nodeDiv.append('<i class="toggleBtn fa fa-' + icon + '-square"></i>');
        }
      } else {
        if (Number(flags.substr(0,1))) {
          $nodeDiv.append('<i class="edge verticalEdge topEdge fa"></i>');
        }
        if(Number(flags.substr(1,1))) {
          $nodeDiv.append('<i class="edge horizontalEdge rightEdge fa"></i>' +
            '<i class="edge horizontalEdge leftEdge fa"></i>');
        }

        if (data.className == 'company-level') {
          titleSymbol = ''
          contentSymbol = 'fa-sitemap'
        } else if (data.className == 'dept-level') {
          titleSymbol = 'fa-sitemap'
          contentSymbol = 'fa-id-card-o'
        } else {
          titleSymbol = 'fa-id-card-o'
          contentSymbol = 'fa-users'
        }
        $nodeDiv.append('<i class="edge verticalEdge bottomEdge fa"></i>')
          .children('.title').prepend('<i class="fa '+ titleSymbol + ' symbol mr-1"></i>');
        $nodeDiv.append('<i class="edge verticalEdge bottomEdge fa"></i>')
          .children('.content').prepend('<i class="fa '+ contentSymbol + ' symbol mr-1"></i>');
      }

      $nodeDiv.on('mouseenter mouseleave', this.nodeEnterLeaveHandler.bind(this));
      $nodeDiv.on('click', this.nodeClickHandler.bind(this));
      $nodeDiv.on('click', '.topEdge', this.topEdgeClickHandler.bind(this));
      $nodeDiv.on('click', '.bottomEdge', this.bottomEdgeClickHandler.bind(this));
      $nodeDiv.on('click', '.leftEdge, .rightEdge', this.hEdgeClickHandler.bind(this));
      $nodeDiv.on('click', '.toggleBtn', this.toggleVNodes.bind(this));

      // allow user to append dom modification after finishing node create of orgchart
      if (opts.createNode) {
        opts.createNode($nodeDiv, data);
      }

      return $nodeDiv;
    },

    render: function() {
        var super_render = this._super;
        var self = this;
        var org_chart = QWeb.render('equip3_hr_masterdata_employee.org_chart_department_template', {
            widget: self,
        });
        $( ".o_control_panel" ).addClass( "o_hidden" );
        $(org_chart).prependTo(self.$el);

        // display filter sections
        self.showFilterSection(self)
        return org_chart;
    },

    showFilterSection: function(event) {
      var self = this;
      var filter_div = document.createElement("div");
      $(filter_div).attr('id','filter-parent').addClass('d-none');

      $('.chart_title').html(
        '<h2>'+
        '<i id="openFilter" class="fa fa-chevron-circle-right mr8"/>' +
        '<i id="closeFilter" class="fa fa-chevron-circle-down d-none mr8"/>' +
        'Organization Hierarchy' +
        '</h2>'
      );
      
      $(document).on('click', '#openFilter', function() {
        $(filter_div).removeClass('d-none');
        $('#openFilter').addClass('d-none');
        $('#closeFilter').removeClass('d-none');
      });

      $(document).on('click', '#closeFilter', function() {
        $(filter_div).addClass('d-none');
        $('#openFilter').removeClass('d-none');
        $('#closeFilter').addClass('d-none');
      });
      
      // display filter by department & job position
      self.filterByDepartment();;
      self.filterByJobPosition();
      $('#chart-container').append(filter_div)
    },

    filterByDepartment: function(event, sort='asc') {
      var self = this;
      this._rpc({
        model: 'hr.department',
        method: 'search_read',
        fields: ['id', 'name']
      }, []).then(function(result){
        if(result){
          var ul = document.createElement("ul");
          $(ul).attr('id','department_filter')
          var li_list = []
          var result = result.slice().sort(function(a, b) {
            if (sort == 'asc') {
              var comparison = a.name.localeCompare(b.name, undefined, { sensitivity: 'accent' });
            } else {
              var comparison = b.name.localeCompare(a.name, undefined, { sensitivity: 'accent' });
            }
            return comparison;
          });
          _.each(result,function(e){
            var li = document.createElement("li");
            $(li).attr('class','department-filter-value')
            li_list.push(li)
            $(li).val(e.id)
            $(li).html('<sapn>'+e.name+'</sapn>')
            ul.appendChild(li)
          })
          if ($("div#dpt_parent").length == 0) {
            $('#filter-parent').prepend('<div id="dpt_parent"><h4><i class="fa fa-folder mr8"/>DEPARTMENT<i id="dept-sort" class="fa fa-caret-down btn btn-sort"/></h4></div>')
          } else {
            $('#department_filter').remove()
            if (sort == 'desc') {
              $('#dept-sort').removeClass('fa-caret-down').addClass('fa-caret-up')
            } else {
              $('#dept-sort').removeClass('fa-caret-up').addClass('fa-caret-down')
            }
          }
          $('#dpt_parent h4').after(ul)
          _.each($('#filter-parent li'),function(my_li){
            my_li.classList.remove("active")
            $(my_li).on('click',function(curr_li){
              if (curr_li.currentTarget.className == 'department-filter-value') {
                _.each($('#filter-parent li'),function(my_li){
                  my_li.classList.remove("active")
                })
                if(!curr_li.currentTarget.classList.contains('active'))
                  curr_li.currentTarget.classList.add("active")

                if (!curr_li.currentTarget.textContent) {
                  clearFilterResult();
                }else {
                  self.filterNodesExt(curr_li.currentTarget.textContent.toLowerCase(), '.dept-level');
                }
              }
            })
          })
        }
      })
    },

    filterByJobPosition: function(event, sort='asc') {
      var self = this;
      this._rpc({
        model: 'hr.job',
        method: 'search_read',
        fields: ['id', 'name']
      }, []).then(function(result){
        if(result){
          var ul = document.createElement("ul");
          $(ul).attr('id','job_position_filter')
          var li_list = []
          var result = result.slice().sort(function(a, b) {
            if (sort == 'asc') {
              var comparison = a.name.localeCompare(b.name, undefined, { sensitivity: 'accent' });
            } else {
              var comparison = b.name.localeCompare(a.name, undefined, { sensitivity: 'accent' });
            }
            return comparison;
          });
          _.each(result,function(e){
            var li = document.createElement("li");
            $(li).attr('class','job-position-filter-value')
            li_list.push(li)
            $(li).val(e.id)
            $(li).html('<sapn>'+e.name+'</sapn>')
            ul.appendChild(li)
          })
          if ($("div#j_pos_parent").length == 0) {
            $('#filter-parent').prepend('<div id="j_pos_parent"><h4><i class="fa fa-folder mr8"/>JOB POSITION<i id="job-sort" class="fa fa-caret-down btn btn-sort"/></h4></div>')
          } else {
            $('#job_position_filter').remove()
            if (sort == 'desc') {
              $('#job-sort').removeClass('fa-caret-down').addClass('fa-caret-up')
            } else {
              $('#job-sort').removeClass('fa-caret-up').addClass('fa-caret-down')
            }
          }
          $('#j_pos_parent h4').after(ul)
          _.each($('#filter-parent li'),function(my_li){
            my_li.classList.remove("active")
            $(my_li).on('click',function(curr_li){
              if (curr_li.currentTarget.className == 'job-position-filter-value') {
                _.each($('#filter-parent li'),function(my_li){
                  my_li.classList.remove("active")
                })
                if(!curr_li.currentTarget.classList.contains('active'))
                  curr_li.currentTarget.classList.add("active")

                if (!curr_li.currentTarget.textContent) {
                  clearFilterResult();
                }else {
                  self.filterNodesExt(curr_li.currentTarget.textContent.toLowerCase(), '.job-level');
                }
              }
            })
          })
        }
      })
    },

    getNodeState: function ($node, relation) {
      var $target = {};
      var relation = relation || 'self';
      if (relation === 'parent') {
        $target = $node.closest('.nodes').siblings(':first');
        if ($target.length) {
          if ($target.is('.hidden') || (!$target.is('.hidden') && $target.closest('.nodes').is('.hidden'))) {
            return { 'exist': true, 'visible': false };
          }
          return { 'exist': true, 'visible': true };
        }
      } else if (relation === 'children') {
        $target = $node.closest('tr').siblings(':last');
        if ($target.length) {
          if (!$target.is('.hidden')) {
            return { 'exist': true, 'visible': true };
          }
          return { 'exist': true, 'visible': false };
        }
      } else if (relation === 'siblings') {
        $target = $node.closest('table').parent().siblings();
        if ($target.length) {
          if (!$target.is('.hidden') && !$target.parent().is('.hidden')) {
            return { 'exist': true, 'visible': true };
          }
          return { 'exist': true, 'visible': false };
        }
      } else {
        $target = $node;
        if ($target.length) {
          if (!(($target.closest('.nodes').length && $target.closest('.nodes').is('.hidden')) ||
            ($target.closest('table').parent().length && $target.closest('table').parent().is('.hidden')) ||
            ($target.parent().is('li') && ($target.closest('ul').is('.hidden') || $target.closest('verticalNodes').is('.hidden')))
          )) {
            return { 'exist': true, 'visible': true };
          }
          return { 'exist': true, 'visible': false };
        }
      }
      return { 'exist': false, 'visible': false };
    },

    isInAction: function ($node) {
      return $node.children('.edge').attr('class').indexOf('fa-') > -1 ? true : false;
    },

    switchHorizontalArrow: function ($node) {
      var opts = this.options;
      if (opts.toggleSiblingsResp && (typeof opts.ajaxURL === 'undefined' || $node.closest('.nodes').data('siblingsLoaded'))) {
        var $prevSib = $node.closest('table').parent().prev();
        if ($prevSib.length) {
          if ($prevSib.is('.hidden')) {
            $node.children('.leftEdge').addClass('fa-chevron-left').removeClass('fa-chevron-right');
          } else {
            $node.children('.leftEdge').addClass('fa-chevron-right').removeClass('fa-chevron-left');
          }
        }
        var $nextSib = $node.closest('table').parent().next();
        if ($nextSib.length) {
          if ($nextSib.is('.hidden')) {
            $node.children('.rightEdge').addClass('fa-chevron-right').removeClass('fa-chevron-left');
          } else {
            $node.children('.rightEdge').addClass('fa-chevron-left').removeClass('fa-chevron-right');
          }
        }
      } else {
        var $sibs = $node.closest('table').parent().siblings();
        var sibsVisible = $sibs.length ? !$sibs.is('.hidden') : false;
        $node.children('.leftEdge').toggleClass('fa-chevron-right', sibsVisible).toggleClass('fa-chevron-left', !sibsVisible);
        $node.children('.rightEdge').toggleClass('fa-chevron-left', sibsVisible).toggleClass('fa-chevron-right', !sibsVisible);
      }
    },

    switchVerticalArrow: function ($arrow) {
      $arrow.toggleClass('fa-chevron-up').toggleClass('fa-chevron-down');
    },

    HideFirstParentEnd: function (event) {
      var $topEdge = event.data.topEdge;
      var $node = $topEdge.parent();
      if (this.isInAction($node)) {
        this.switchVerticalArrow($topEdge);
        this.switchHorizontalArrow($node);
      }
    },

    hideParentEnd: function (event) {
      $(event.target).removeClass('sliding');
      event.data.upperLevel.addClass('hidden').slice(1).removeAttr('style');
    },

    hideParent: function ($node) {
      var $upperLevel = $node.closest('.nodes').siblings();
      if ($upperLevel.eq(0).find('.spinner').length) {
        $node.closest('.orgchart').data('inAjax', false);
      }
      // hide the sibling nodes
      if (this.getNodeState($node, 'siblings').visible) {
        this.hideSiblings($node);
      }
      // hide the lines
      var $lines = $upperLevel.slice(1);
      $lines.css('visibility', 'hidden');
      // hide the superior nodes with transition
      var $parent = $upperLevel.eq(0).find('.node');
      if (this.getNodeState($parent).visible) {
        $('.node').css('transition','transform 0.001s, opacity 0.001s')
        $parent.addClass('sliding slide-down').one('transitionend', { 'upperLevel': $upperLevel }, this.hideParentEnd);
      }
      // if the current node has the parent node, hide it recursively
      if (this.getNodeState($parent, 'parent').visible) {
        this.hideParent($parent);
      }
    },

    topEdgeHandler: function (node) {
      var $topEdge = $(node.children('.topEdge'));
      var $node = node;
      var parentState = this.getNodeState($node, 'parent');
      if (parentState.exist) {
        var $parent = $node.closest('table').closest('tr').siblings(':first').find('.node');
        if ($parent.is('.sliding')) { return; }
        // hide the ancestor nodes and sibling nodes of the specified node
        if (parentState.visible) {
          this.hideParent($node);
          $parent.one('transitionend', { 'topEdge': $topEdge }, this.HideFirstParentEnd.bind(this));
        }
      }
    },

    isVisibleNode: function (index, elem) {
      return this.getNodeState($(elem)).visible;
    },

    stopAjax: function ($nodeLevel) {
      if ($nodeLevel.find('.spinner').length) {
        $nodeLevel.closest('.orgchart').data('inAjax', false);
      }
    },

    repaint: function (node) {
      if (node) {
        node.style.offsetWidth = node.offsetWidth;
      }
    },

    hideChildrenEnd: function (event) {
      var $node = event.data.node;
      event.data.animatedNodes.removeClass('sliding');
      if (event.data.isVerticalDesc) {
        event.data.lowerLevel.addClass('hidden');
      } else {
        event.data.animatedNodes.closest('.nodes').prevAll('.lines').removeAttr('style').addBack().addClass('hidden');
        event.data.lowerLevel.last().find('.verticalNodes').addClass('hidden');
      }
      if (this.isInAction($node)) {
        this.switchVerticalArrow($node.children('.bottomEdge'));
      }
    },

    hideChildren: function ($node) {
      var $lowerLevel = $node.closest('tr').siblings();
      this.stopAjax($lowerLevel.last());
      var $animatedNodes = $lowerLevel.last().children(':not(.hidden)').find('.node').filter(this.isVisibleNode.bind(this));
      var isVerticalDesc = $lowerLevel.last().is('.verticalNodes') ? true : false;
      if (!isVerticalDesc) {
        $animatedNodes.closest('table').closest('tr').prevAll('.lines').css('visibility', 'hidden');
      }
      this.repaint($animatedNodes.get(0));
      $animatedNodes.addClass('sliding slide-up').eq(0).one('transitionend', { 'animatedNodes': $animatedNodes, 'lowerLevel': $lowerLevel, 'isVerticalDesc': isVerticalDesc, 'node': $node }, this.hideChildrenEnd.bind(this));
    },

    bottomEdgeHandler: function (node) {
      var bottomEdge = $(node.children('.bottomEdge'));
      var $node = node;
      var childrenState = this.getNodeState($node, 'children');
      if (childrenState.exist) {
        var $children = $node.closest('tr').siblings(':last');
        if ($children.find('.sliding').length) { return; }
        // hide the ancestor nodes and sibling nodes of the specified node
        if (childrenState.visible) {
          this.hideChildren($node);
        }
      }
    },

    filterNodesExt: function (keyWord, nodeType='.node') {
			var show = false;
      var self = this
			clearFilterResult();
			if(!keyWord.length) {
			  clearFilterResult();
			  window.alert('Please type key word firstly.');
			  return;
			} else {
			  var $chart = $('.orgchart');
        //show all hidden
        $chart.find('.slide-down').each(function(index, node) {
          $(node).removeClass('slide-down')
        });
        $chart.find(':hidden').each(function(index, node) {
          $(node).removeClass('hidden').css('visibility','visible');
        });
			  // disalbe the expand/collapse feture
			  // $chart.addClass('noncollapsable');
			  // distinguish the matched nodes and the unmatched nodes according to the given key word
			  $chart.find(nodeType).filter(function(index, node) {
				  // suppression des précédents noeuds qui ont matchés
				  $(node).removeClass('matched');
				  if ($(node).text().toLowerCase().indexOf(keyWord) > -1){
					show = true;
				  }
				  return $(node).text().toLowerCase().indexOf(keyWord) > -1;
				}).addClass('matched')
				.closest('table').parents('table').find('tr:first').find('.node').addClass('retained');
			  // hide the unmatched nodes
			  $chart.find('.matched,.retained').each(function(index, node) {
				$(node).removeClass('slide-up')
				  .closest('.nodes').removeClass('hidden')
				  .siblings('.lines').removeClass('hidden');
				var $unmatched = $(node).closest('table').parent().siblings().find('.node:first:not(.matched,.retained)')
				  .closest('table').parent().addClass('hidden');
				$unmatched.parent().prev().children().slice(1, $unmatched.length * 2 + 1).addClass('hidden');
			  });
			  // hide the redundant descendant nodes of the matched nodes
			  // $chart.find('.matched').each(function(index, node) {
  			// 	if (!$(node).closest('tr').siblings(':last').find('.matched').length) {
  			// 	  $(node).closest('tr').siblings().addClass('hidden');
  			// 	}
			  // });

        //hide the matched node parents in department filter
        if (nodeType == '.dept-level') {
          $chart.find('.matched').each(function(index, node) {
            self.topEdgeHandler($(node))
          });
        }
        
			  if (!show){
				$("#chart-container").addClass('hidden');
			  }else{
				$("#chart-container").removeClass('hidden');
			  }
			}
    },

    reload_org_chart: function(event) {
        $("#org-chart-main").remove();
        this.show_org_chart();
    },

    open_employee_data: function(event) {
      // Open employee data by job position
      var self = this;
      self._rpc({
          model:'ir.model.data',
          method:'xmlid_to_res_model_res_id',
          args: ['equip3_hr_masterdata_employee.employee_tree_view_for_org_hierarchy'],
      }).then(function(data){                
          self.do_action({
              name: 'Employee by Job Position',
              type: 'ir.actions.act_window',
              res_model: 'hr.employee',
              view_mode: 'tree,form',
              target: 'new',
              limit: 7,
              context: {
                'hide_create_button': true,
              },
              domain: '[["job_id", "=",' + job_id + '],["contract_state", "=", "open"]]',
              views: [[data[1], 'list']],
          });
      });

        // event.preventDefault();
        // var employeeDataDiv = $(event.currentTarget.parentElement.nextElementSibling)
        // if (employeeDataDiv.css('display') == 'none') {
        //     employeeDataDiv.css('display', 'block')
        // } else {
        //     employeeDataDiv.css('display', 'none')
        // }
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

    show_org_chart: function (event) {
        var self = this;
        self._rpc({
            model: 'org.chart.department',
            method: 'get_department_data',
        }, []).then(function(result){
            department_data = result;
        }).then(function(){
            self.render();
          self.href = window.location.href;
        }).then(function() {
            oc = get_organization_dept_chart(department_data.values, direction, verticalLevel);
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
            if (direction != undefined && direction == 'l2r') {
                $('#org-chart-main').addClass('org-chart-scroll');
            }

            var $deptNodes = $('.orgchart').find('.nodes').eq(0).find('.dept-level')
            $deptNodes.each(function(index, node) {
              self.bottomEdgeHandler($(node))
            });
        });
    },

    switch_org_chart: function(event) {
      direction = get_direction(direction);
      this.reload_org_chart();
    },

    export_org_chart: function (event) {
      var self = this;
      self._rpc({
          model:'ir.model.data',
          method:'xmlid_to_res_model_res_id',
          args: ['equip3_hr_masterdata_employee.org_chart_export_type_form_view'],
      }).then(function(data){                
          // Call transient model form
          self.do_action({
              name: 'Organization Chart Export Type',
              type: 'ir.actions.act_window',
              res_model: 'org.chart.export.type',
              target: 'new',
              views: [[data[1], 'form']],
          });
      });
    },

    click_search_job_position: function (event) {
      var keyWord = $('#key-word').val()
      var type = '.job-level'
      filterNodes(keyWord, type);
      $('#key-word').val('')
      $('.o_searchview_hierarchy_autocomplete').removeClass('show')
    },

    click_search_dept: function (event) {
      var keyWord = $('#key-word').val()
      var type = '.dept-level'
      this.filterNodesExt(keyWord, '.dept-level');
      $('#key-word').val('')
      $('.o_searchview_hierarchy_autocomplete').removeClass('show')
    },
  });

  core.action_registry.add('equip3_hr_masterdata_employee.org_chart_department', OrgChartDepartment);
  return OrgChartDepartment;
});

odoo.define('equip3_hr_masterdata_employee.employee_tree_view_for_org_hierarchy', function (require) {
  'use strict';

  $(document).on('click', function (ev) {
    var $modal = $('.modal:visible');
    var $employee_tree_view_hierarchy = $('.employee_tree_view_hierarchy:visible')
    if ($modal.length && $employee_tree_view_hierarchy.length && $modal.is(ev.target) == true && $modal.has(ev.target).length === 0) {
      $modal.css('display','none');
    }
  });
});