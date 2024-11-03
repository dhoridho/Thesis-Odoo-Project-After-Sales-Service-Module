<html>
<head>
    <style type="text/css">
        table #head {
        	width:100%;
        }
        .list_table0 {
			font-size:18px;
			font-weight:bold;
			padding-top:10px;
			padding-bottom:10px;
			padding-right:15%;
			width:70%;
			border-collapse:collapse;
        	border-top:1px solid white;
        	border-bottom:1px solid white;
        	border-left:1px solid white;
		}
		.list_table1{
			width:100%;
			font-size:11px;
			border-left:1px solid black;
			border-top:1px solid black;
        	border-bottom:1px solid black;
        	border-right:1px solid black;
		}
		.list_table2 {
			font-size:10px;
		}
		.list_table3 {
			font-size:10px;
		}
		.list_table4 {
			font-size:10px;
			padding-top:5px;
			padding-bottom:5px;
		}
		.cust_info
			{
			font-size:10px;
			font-weight:bold;
			border-top:1px solid black;
			border-bottom:1px solid black;
			border-left:1px solid black;
			border-right:1px solid black;
			padding-top:6px;
			padding-bottom:6px;
			}
		.inv_line td
			{
			border-top:0px;
			border-bottom:0px;
			}
    </style>
</head>
<body>
<br/>
    %for vcr in objects:
	<table width="100%" class="list_table1" cellpadding="3">
	    <tr valign="top">
	    	<td width="100%" colspan="6" style="font-size:14" align="center"><u>BUKTI ${ vcr.journal_id.type == 'bank' and 'BANK' or vcr.journal_id.type == 'cash' and 'KAS' or vcr.journal_id.type == 'sale' and 'PIUTANG' or vcr.journal_id.type == 'purchase' and 'HUTANG' or vcr.journal_id.type in ('sale_advance','purchase_advance') and 'DOWNPAYMENT' or 'GENERAL'} ${ vcr.voucher_type == 'sale' and 'MASUK' or 'KELUAR'}</u></td>
	    </tr>
	    <tr valign="top">
	    	<td width="14%">${ vcr.voucher_type == 'sale' and 'Diterima Oleh' or 'Dibayarkan Kepada'}</td>
	    	<td width="1%">:</td>
	    	<td width="35%">${vcr.partner_id.name or ''}</td>
	    	<td width="14%">Voucher No.</td>
	    	<td width="1%">:</td>
	    	<td width="35%">${vcr.number or ''}</td>
	    </tr>
	    <tr valign="top">
	    	<td width="14%">Uang Sejumlah</td>
	    	<td width="1%">:</td>
	    	<td width="35%">${ vcr.currency_id.symbol or '' }. ${ formatLang(vcr.amount) or 0}</td>
	    	<td width="14%">Tanggal</td>
	    	<td width="1%">:</td>
	    	<td width="35%">${time.strftime('%d %b %Y', time.strptime(vcr.account_date,'%Y-%m-%d')) or ''}</td>
	    </tr>
	    <tr valign="top">
	    	<td width="14%">Terbilang</td>
	    	<td width="1%">:</td>
	    	<td width="35%"><i>( ${ vcr.check_amount_in_words_id or ''} )</i></td>
	    	<td width="14%">Tipe Pembayaran</td>
	    	<td width="1%">:</td>
	    	<td width="35%">${vcr.journal_id.name or ''}
	    	</td>
	    </tr>
	    <tr valign="top">
	    	<td width="14%">Memo</td>
	    	<td width="1%">:</td>
	    	<td width="35%" colspan="4">${ vcr.name or ''}</td>
	    </tr>
    </table>
    <table class="list_table1" border="1" style="border-collapse:collapse;" width="100%" cellpadding="3">
    	<tr class='inv_line'>
        	<th>No.</th>
            <th>Description</th>
            <th>No. Akun</th>
            <th>Nama Akun</th>
            <th>Jumlah</th>
        </tr>
    	<% set i = 1 %>
		<% set blank = blank_line(vcr.line_ids) %>	
		%for line in vcr.line_ids:
	        <tr class='inv_line'>
	        	<td style="text-align:center;">${i}. </td>
	        	<td style="text-align:left;">${line.name or ''}</td>
	        	<td style="text-align:center;">${line.account_id.code or ''}</td>
	        	<td style="text-align:left;">${line.account_id.name or ''}</td>
	        	<td style="text-align:right;">${ formatLang(line.price_subtotal) or ''}</td>
	        </tr>
	   	<% set i = i + 1 %>
        %endfor
        %for count in range(0,16-blank):
        <tr class='inv_line'>
        	<td style="text-align:left;"></td>
        	<td style="text-align:right;"></td>
        	<td style="text-align:right;"></td>
        	<td style="text-align:right;"></td>
        	<td style="text-align:right;"></td>
        </tr>
	    %endfor
	    <table border="0" width="100%" cellpadding="3" style="font-size:11px;">
	        <tr style="text-align:center;">
	        	<td>Pembukuan</td>
	        	<td>Mengetahui</td>
	        	<td>Menyetujui</td>
	        	<td>Kasir</td>
	        	<td>Penerima</td>
	        </tr>
	        <tr style="text-align:center;">
	        	<td valign="bottom">( ________________ )</td>
	        	<td valign="bottom">( ________________ )</td>
	        	<td valign="bottom">( ________________ )</td>
	        	<td valign="bottom"><br/><br/><br/><br/>( ________________ )</td>
	        	<td valign="bottom">( ________________ )</td>
	        </tr>
        </table>
    </table>
    %endfor
</body>
</html>
