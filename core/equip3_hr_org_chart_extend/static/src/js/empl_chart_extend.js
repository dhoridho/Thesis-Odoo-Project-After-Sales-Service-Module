odoo.define("equip3_hr_org_chart_extend.empl_chart_extend", function(require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var OrgChartEmployeeExtend = require('org_chart_premium.org_chart');

    var OrgChartEmployeeExt = OrgChartEmployeeExtend.include({
        init: function(parent, context) {
			this._super(parent, context);
		},
		render: function() {
			var res = this._super();
			var self = this;
			self.showFilterSection(self)
			$( document ).ready(function() {
				var h_chart = document.getElementsByClassName("orgchart")
				if(h_chart.length > 0){
					if(h_chart[0].classList.contains('l2r')){
						h_chart[0].classList.remove('l2r')
					}else{
						h_chart[0].classList.add('l2r')
					}
				}
			})
			return res;
		},

		showFilterSection: function(event) {
	      var self = this;
	      var filter_div = document.createElement("div");
	      $(filter_div).attr('id','filter-parent').addClass('d-none');

	      $('.chart_title_employee').html(
	        '<h2>'+
	        '<i id="openFilter" class="fa fa-chevron-circle-right mr8"/>' +
	        '<i id="closeFilter" class="fa fa-chevron-circle-down d-none mr8"/>' +
	        'Employee Hierarchy' +
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
	      self.filterByDepartment();
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
	              _.each($('#filter-parent li'),function(my_li){
	                my_li.classList.remove("active")
	              })
	              if(!curr_li.currentTarget.classList.contains('active'))
	                curr_li.currentTarget.classList.add("active")

	              if (!curr_li.currentTarget.textContent) {
	                clearFilterResult();
	              }else {
	                self.filterNodesExt(curr_li.currentTarget.textContent.toLowerCase());
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
	              _.each($('#filter-parent li'),function(my_li){
	                my_li.classList.remove("active")
	              })
	              if(!curr_li.currentTarget.classList.contains('active'))
	                curr_li.currentTarget.classList.add("active")

	              if (!curr_li.currentTarget.textContent) {
	                clearFilterResult();
	              }else {
	                self.filterNodesExt(curr_li.currentTarget.textContent.toLowerCase());
	              }
	            })
	          })
	        }
	      })
	    },

		filterNodesExt: function (keyWord) {
			var show = false;
			clearFilterResult();
			if(!keyWord.length) {
			  clearFilterResult();
			  window.alert('Please type key word firstly.');
			  return;
			} else {
			  var $chart = $('.orgchart');
			  // disalbe the expand/collapse feture
			  // $chart.addClass('noncollapsable');
			  // distinguish the matched nodes and the unmatched nodes according to the given key word
			  $chart.find('.node').filter(function(index, node) {
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
			  $chart.find('.matched').each(function(index, node) {
				if (!$(node).closest('tr').siblings(':last').find('.matched').length) {
				  $(node).closest('tr').siblings().addClass('hidden');
				}
			  });

			  if (!show){
				$("#chart-container").addClass('hidden');
			  }else{
				$("#chart-container").removeClass('hidden');
			  }
			}
		  },
    })
    return OrgChartEmployeeExt;

});