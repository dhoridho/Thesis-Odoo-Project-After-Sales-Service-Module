var nodeTemplate = function(data) {
      return `
        <span class="office">${data.office}</span>
        <div class="title">${data.name}</div>
        <div class="content">${data.title}</div>
      `;
    };

function get_organization_chart(datascource, direction, verticalLeve, isPermitted) {
  var oc = $('#chart-container').orgchart({
    'data' : datascource,
    'nodeTemplate': nodeTemplate,
    'toggleSiblingsResp': true,
    'draggable': isPermitted,
    'exportFilename': 'OrgChartEmployeePro',
    'verticalLevel': verticalLevel,
    'direction': direction,
    'dropCriteria': function($draggedNode, $dragZone, $dropZone) {
      if($draggedNode.find('.content').text().indexOf('manager') > -1 && $dropZone.find('.content').text().indexOf('engineer') > -1) {
        return false;
      }
      return true;
    },
    'createNode': function($node, data) {
      // Display create, edit, and delete button if user group is not Self Service
      if (isPermitted) {
        var secondMenuIcon = $('<i>', {
          'class': 'fa fa-info-circle third-menu-icon',
          click: function() {
            $(this).siblings('.third-menu').toggle();
          }
        });
        var secondMenu = '<div class="third-menu">';
        secondMenu += '<img class="avatar add_node" title="Add New Child" id="' + data.id + '" src="/org_chart_premium/static/src/img/add.png">';
        if (data.id != -1){
          secondMenu += '<img class="avatar edit_node" title="Edit Department" id="' + data.id + '" src="/org_chart_premium/static/src/img/edit.png"><img class="avatar delete_node" title="Delete Department" id="' + data.id + '" src="/org_chart_premium/static/src/img/delete.png">';
        }
        secondMenu += '</div>';
        $node.append(secondMenuIcon).append(secondMenu);
      }
    }
  });

  // Disbale expand/collapse feature if current user group is a Self Service
  if (!isPermitted) {
    var $chart = $('.orgchart');
    $chart.addClass('noncollapsable');
  }
  return oc;
}

function filterNodes(keyWord, nodeType='.node') {
    var show = false;
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

      $('.o_searchview_hierarchy_autocomplete').addClass('show')
      $('.keyword').each(function(index, node) {
        $(node).text(keyWord)
      });
    }
  }

function clearFilterResult() {
  $('.orgchart').removeClass('noncollapsable')
    .find('.node').removeClass('matched retained')
    .end().find('.hidden').removeClass('hidden')
    .end().find('.slide-up, .slide-left, .slide-right').removeClass('slide-up slide-right slide-left');
  $("#chart-container").removeClass('hidden');
  $('.o_searchview_hierarchy_autocomplete').removeClass('show')
}

function resize_window(currZoom, step, callback) {
  if ($.browser.mozilla){
      currZoom -= step;
      $('body').css('MozTransform','scale(' + currZoom + ')');

  } else {
      currZoom -= step;
      $('body').css('zoom', ' ' + currZoom + '%');
  }
  callback();

  return currZoom;
}

function get_direction(current_direction) {
  if (current_direction == 'l2r'){
    return false;
  }
  return 'l2r';
}
